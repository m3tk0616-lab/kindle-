"""In-memory job queue with SSE-based progress broadcasting."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator


class JobStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    STOPPED   = "stopped"


@dataclass
class Job:
    id: str
    name: str
    mode: str               # "android" | "desktop"
    device_serial: str
    save_dir: str
    total_pages: int        # 0 = unlimited
    auto_pdf: bool
    auto_ocr: bool
    api_key: str

    status: JobStatus = JobStatus.PENDING
    page_count: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    error: str = ""
    pdf_path: str = ""
    logs: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode,
            "save_dir": self.save_dir,
            "status": self.status,
            "page_count": self.page_count,
            "total_pages": self.total_pages,
            "auto_pdf": self.auto_pdf,
            "auto_ocr": self.auto_ocr,
            "pdf_path": self.pdf_path,
            "error": self.error,
            "logs": self.logs[-20:],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._stop_flags: dict[str, bool] = {}
        self._subscribers: list[asyncio.Queue] = []

    # ── CRUD ─────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        mode: str,
        device_serial: str,
        save_dir: str,
        total_pages: int = 0,
        auto_pdf: bool = True,
        auto_ocr: bool = False,
        api_key: str = "",
    ) -> Job:
        job = Job(
            id=uuid.uuid4().hex[:10],
            name=name,
            mode=mode,
            device_serial=device_serial,
            save_dir=save_dir,
            total_pages=total_pages,
            auto_pdf=auto_pdf,
            auto_ocr=auto_ocr,
            api_key=api_key,
        )
        self._jobs[job.id] = job
        self._stop_flags[job.id] = False
        self._broadcast(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    # ── State updates ─────────────────────────────────────────────

    def set_status(self, job_id: str, status: JobStatus, error: str = ""):
        job = self._jobs[job_id]
        job.status = status
        if error:
            job.error = error
        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.STOPPED):
            job.completed_at = time.time()
        self._broadcast(job)

    def increment_page(self, job_id: str):
        job = self._jobs[job_id]
        job.page_count += 1
        self._broadcast(job)

    def log(self, job_id: str, message: str):
        job = self._jobs[job_id]
        ts = time.strftime("%H:%M:%S")
        job.logs.append(f"[{ts}] {message}")
        self._broadcast(job)

    def set_pdf(self, job_id: str, pdf_path: str):
        job = self._jobs[job_id]
        job.pdf_path = pdf_path
        self._broadcast(job)

    # ── Stop control ──────────────────────────────────────────────

    def request_stop(self, job_id: str):
        self._stop_flags[job_id] = True

    def should_stop(self, job_id: str) -> bool:
        return self._stop_flags.get(job_id, False)

    # ── SSE broadcasting ──────────────────────────────────────────

    async def subscribe(self) -> AsyncGenerator[dict, None]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        try:
            while True:
                data = await q.get()
                yield data
        finally:
            self._subscribers.remove(q)

    def _broadcast(self, job: Job):
        data = job.as_dict()
        for q in self._subscribers:
            q.put_nowait(data)
