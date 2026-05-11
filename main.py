"""
Kindle Screenshot Automation — high-performance background processor
- Page-change detection (perceptual hash)
- Auto PDF + OCR on completion
- SSE-based real-time progress
- Job queue for multiple books
"""

import asyncio
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from modules.adb_controller import AdbController
from modules.desktop_controller import DesktopController
from modules.job_manager import JobManager, JobStatus
from modules.ocr_engine import OcrEngine
from modules.page_detector import PageChangeWaiter
from modules.pdf_builder import build_pdf
from modules.prompt_parser import PromptParser

app = FastAPI(title="Kindle Screenshot Automation")

JOBS_ROOT = Path("jobs")
JOBS_ROOT.mkdir(exist_ok=True)

adb     = AdbController()
desktop = DesktopController()
jobs    = JobManager()
parser  = PromptParser()


# ── Request models ──────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    name: str = "新しい本"
    mode: str = "android"           # "android" | "desktop"
    device_serial: str = ""
    total_pages: int = 0            # 0 = unlimited
    auto_pdf: bool = True
    auto_ocr: bool = False
    api_key: str = ""               # Claude API key for OCR / prompt parsing

class OcrRequest(BaseModel):
    job_id: str
    api_key: str = ""

class ParseRequest(BaseModel):
    chat_text: str
    api_key: str = ""


# ── Static files ────────────────────────────────────────────────

app.mount("/jobs",   StaticFiles(directory="jobs"),   name="jobs")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")


# ── Device info ─────────────────────────────────────────────────

@app.get("/api/devices")
async def list_devices():
    try:
        devices = adb.list_devices()
        return {"devices": devices}
    except Exception as e:
        return {"devices": [], "warning": str(e)}

@app.get("/api/screen-info")
async def screen_info(device_serial: str = ""):
    try:
        w, h = adb.get_screen_size(device_serial)
        return {"width": w, "height": h, "megapixels": round(w * h / 1_000_000, 1)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/screenshot/preview")
async def preview_screenshot(device_serial: str = ""):
    tmp = str(JOBS_ROOT / "_preview.png")
    try:
        adb.capture(device_serial, tmp)
        return FileResponse(tmp, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Job management ──────────────────────────────────────────────

@app.get("/api/jobs")
async def list_jobs():
    return {"jobs": [j.as_dict() for j in jobs.list()]}

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.as_dict()

@app.post("/api/jobs")
async def create_job(req: CreateJobRequest, background_tasks: BackgroundTasks):
    save_dir = str(JOBS_ROOT / f"job_{int(time.time() * 1000)}")
    job = jobs.create(
        name=req.name,
        mode=req.mode,
        device_serial=req.device_serial,
        save_dir=save_dir,
        total_pages=req.total_pages,
        auto_pdf=req.auto_pdf,
        auto_ocr=req.auto_ocr,
        api_key=req.api_key or os.getenv("ANTHROPIC_API_KEY", ""),
    )
    background_tasks.add_task(_run_job, job.id)
    return job.as_dict()

@app.post("/api/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    if not jobs.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    jobs.request_stop(job_id)
    return {"status": "stop_requested"}

@app.post("/api/jobs/{job_id}/pdf")
async def build_job_pdf(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        pdf_path = build_pdf(job.save_dir)
        jobs.set_pdf(job_id, pdf_path)
        return {"pdf_path": pdf_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}/download")
async def download_pdf(job_id: str):
    job = jobs.get(job_id)
    if not job or not job.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        job.pdf_path,
        media_type="application/pdf",
        filename=f"{job.name}.pdf",
    )

@app.post("/api/jobs/{job_id}/ocr")
async def run_ocr(job_id: str, req: OcrRequest, background_tasks: BackgroundTasks):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    background_tasks.add_task(_run_ocr_task, job_id, req.api_key)
    return {"status": "ocr_started"}

@app.get("/api/jobs/{job_id}/screenshots")
async def list_screenshots(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    p = Path(job.save_dir)
    if not p.exists():
        return {"files": []}
    files = sorted(f.name for f in p.glob("page_*.png"))
    return {"files": files, "dir": str(p)}


# ── SSE progress stream ─────────────────────────────────────────

@app.get("/api/events")
async def sse_events(request: Request):
    async def generator():
        for job in jobs.list():
            yield {"data": json.dumps(job.as_dict())}
        async for data in jobs.subscribe():
            if await request.is_disconnected():
                break
            yield {"data": json.dumps(data)}
    return EventSourceResponse(generator())


# ── Prompt parser ───────────────────────────────────────────────

@app.post("/api/parse-prompt")
async def parse_prompt(req: ParseRequest):
    try:
        return await parser.extract_settings(req.chat_text, req.api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Background job runner ───────────────────────────────────────

async def _run_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return

    save_dir = Path(job.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    jobs.set_status(job_id, JobStatus.RUNNING)
    jobs.log(job_id, f"開始: {job.name} ({job.mode}モード)")

    def _capture(path: str) -> str:
        if job.mode == "android":
            return adb.capture(job.device_serial, path)
        return desktop.capture(path)

    def _next_page():
        if job.mode == "android":
            adb.swipe_next_page(job.device_serial)
        else:
            desktop.press_right()

    tmp_path = str(save_dir / "_tmp_poll.png")
    waiter = PageChangeWaiter(capture_fn=_capture, timeout=15.0, poll_interval=0.4)

    try:
        # Capture first page
        first_path = str(save_dir / f"page_{job.page_count + 1:04d}.png")
        await asyncio.get_running_loop().run_in_executor(None, _capture, first_path)
        jobs.increment_page(job_id)
        jobs.log(job_id, f"ページ 1 保存")

        while not jobs.should_stop(job_id):
            if job.total_pages and job.page_count >= job.total_pages:
                jobs.log(job_id, f"指定ページ数 ({job.total_pages}) に到達")
                break

            last_path = str(save_dir / f"page_{job.page_count:04d}.png")

            # Trigger page turn
            await asyncio.get_running_loop().run_in_executor(None, _next_page)

            # Wait for screen to actually change
            changed = await asyncio.get_running_loop().run_in_executor(
                None, waiter.wait_for_change, last_path, tmp_path
            )

            if not changed:
                jobs.log(job_id, "ページ変化なし — 最終ページに到達した可能性があります")
                break

            # Save the new page
            next_path = str(save_dir / f"page_{job.page_count + 1:04d}.png")
            Path(tmp_path).rename(next_path)
            jobs.increment_page(job_id)

            page_n = jobs.get(job_id).page_count
            if page_n % 10 == 0:
                jobs.log(job_id, f"{page_n} ページ完了")

        # Post-processing
        if job.auto_pdf and jobs.get(job_id).page_count > 0:
            jobs.log(job_id, "PDF を生成中...")
            try:
                pdf_path = await asyncio.get_running_loop().run_in_executor(
                    None, build_pdf, save_dir
                )
                jobs.set_pdf(job_id, pdf_path)
                jobs.log(job_id, f"PDF 生成完了: {pdf_path}")
            except Exception as e:
                jobs.log(job_id, f"PDF 生成失敗: {e}")

        if job.auto_ocr and job.api_key:
            await _run_ocr_task(job_id, job.api_key)

        final_status = (
            JobStatus.STOPPED if jobs.should_stop(job_id) else JobStatus.COMPLETED
        )
        jobs.set_status(job_id, final_status)
        jobs.log(job_id, f"完了 — {jobs.get(job_id).page_count} ページ取得")

    except Exception as e:
        jobs.set_status(job_id, JobStatus.FAILED, error=str(e))
        jobs.log(job_id, f"エラー: {e}")


async def _run_ocr_task(job_id: str, api_key: str):
    job = jobs.get(job_id)
    if not job:
        return
    jobs.log(job_id, "OCR 開始...")
    key = api_key or job.api_key or os.getenv("ANTHROPIC_API_KEY", "")
    ocr = OcrEngine(api_key=key)

    done = 0
    def _progress(d, total):
        nonlocal done
        done = d
        jobs.log(job_id, f"OCR: {d}/{total} ページ")

    try:
        await ocr.ocr_directory(job.save_dir, progress_cb=_progress)
        jobs.log(job_id, "OCR 完了 — .txt ファイルを各ページと同フォルダに保存しました")
    except Exception as e:
        jobs.log(job_id, f"OCR エラー: {e}")
