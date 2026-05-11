"""
Kindle Screenshot Automation Server
Cross-platform: Android (ADB) / Desktop (pyautogui) / Web UI
"""

import asyncio
import json
import os
import time
from pathlib import Path

import aiofiles
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from modules.adb_controller import AdbController
from modules.desktop_controller import DesktopController
from modules.prompt_parser import PromptParser

app = FastAPI(title="Kindle Screenshot Automation")

SCREENSHOTS_DIR = Path("screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

adb = AdbController()
desktop = DesktopController()
parser = PromptParser()

_running = False
_task: asyncio.Task | None = None
_page_count = 0


# ── Request models ──────────────────────────────────────────────

class StartRequest(BaseModel):
    mode: str = "android"       # "android" | "desktop"
    interval: float = 3.0       # seconds between pages
    total_pages: int = 0        # 0 = unlimited
    save_dir: str = "screenshots"
    device_serial: str = ""     # ADB serial (empty = first device)

class ParseRequest(BaseModel):
    chat_text: str
    api_key: str = ""           # Claude API key (optional; falls back to ANTHROPIC_API_KEY env)

class TapRequest(BaseModel):
    x: int
    y: int
    device_serial: str = ""


# ── Static files & root ─────────────────────────────────────────

app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")


# ── Device info ─────────────────────────────────────────────────

@app.get("/api/devices")
async def list_devices():
    return {"devices": adb.list_devices()}

@app.get("/api/screenshot/preview")
async def preview_screenshot(device_serial: str = ""):
    """Single screenshot for live preview."""
    try:
        path = adb.capture(device_serial, str(SCREENSHOTS_DIR / "_preview.png"))
        return FileResponse(path, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Automation control ──────────────────────────────────────────

@app.post("/api/start")
async def start_automation(req: StartRequest, background_tasks: BackgroundTasks):
    global _running, _task
    if _running:
        raise HTTPException(status_code=409, detail="Already running")

    save_dir = Path(req.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    _running = True
    background_tasks.add_task(_run_loop, req, save_dir)
    return {"status": "started"}

@app.post("/api/stop")
async def stop_automation():
    global _running
    _running = False
    return {"status": "stopped"}

@app.get("/api/status")
async def get_status():
    return {"running": _running, "page_count": _page_count}

@app.get("/api/screen-info")
async def screen_info(device_serial: str = ""):
    """Return native screen resolution of the connected Android device."""
    try:
        w, h = adb.get_screen_size(device_serial)
        return {"width": w, "height": h, "megapixels": round(w * h / 1_000_000, 1)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tap")
async def manual_tap(req: TapRequest):
    """Tap a specific coordinate on the Android screen."""
    try:
        adb.tap(req.device_serial, req.x, req.y)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Screenshot listing ──────────────────────────────────────────

@app.get("/api/screenshots")
async def list_screenshots(dir: str = "screenshots"):
    p = Path(dir)
    if not p.exists():
        return {"files": []}
    files = sorted(
        [f.name for f in p.glob("*.png") if not f.name.startswith("_")],
        reverse=True,
    )
    return {"files": files, "dir": str(p)}


# ── Prompt parser ───────────────────────────────────────────────

@app.post("/api/parse-prompt")
async def parse_prompt(req: ParseRequest):
    """Send chat history to Claude API and extract automation settings."""
    try:
        result = await parser.extract_settings(req.chat_text, req.api_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Background loop ─────────────────────────────────────────────

async def _run_loop(req: StartRequest, save_dir: Path):
    global _running, _page_count
    _page_count = 0
    try:
        while _running:
            if req.total_pages and _page_count >= req.total_pages:
                break

            ts = int(time.time() * 1000)
            filename = str(save_dir / f"page_{_page_count + 1:04d}_{ts}.png")

            if req.mode == "android":
                adb.capture(req.device_serial, filename)
                adb.swipe_next_page(req.device_serial)
            else:
                desktop.capture(filename)
                desktop.press_right()

            _page_count += 1
            await asyncio.sleep(req.interval)
    finally:
        _running = False
