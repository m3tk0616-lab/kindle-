"""Android ADB controller — screenshot & page-turn via adb shell."""

import subprocess
import tempfile
from pathlib import Path


class AdbController:
    def _run(self, args: list[str], check=True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["adb"] + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def _serial_prefix(self, serial: str) -> list[str]:
        return ["-s", serial] if serial else []

    def list_devices(self) -> list[dict]:
        result = self._run(["devices", "-l"], check=False)
        devices = []
        for line in result.stdout.splitlines()[1:]:
            line = line.strip()
            if not line or "offline" in line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                info = {"serial": parts[0]}
                for p in parts[2:]:
                    if ":" in p:
                        k, v = p.split(":", 1)
                        info[k] = v
                devices.append(info)
        return devices

    def capture(self, serial: str, save_path: str) -> str:
        """Take a screenshot and pull it to save_path. Returns save_path."""
        remote = "/data/local/tmp/_kindle_ss.png"
        prefix = self._serial_prefix(serial)
        self._run(prefix + ["shell", "screencap", "-p", remote])
        self._run(prefix + ["pull", remote, save_path])
        return save_path

    def tap(self, serial: str, x: int, y: int):
        prefix = self._serial_prefix(serial)
        self._run(prefix + ["shell", "input", "tap", str(x), str(y)])

    def swipe_next_page(self, serial: str):
        """Swipe left to go to the next Kindle page."""
        prefix = self._serial_prefix(serial)
        # swipe from right-center to left-center
        self._run(prefix + ["shell", "input", "swipe", "900", "500", "100", "500", "300"])

    def swipe_prev_page(self, serial: str):
        prefix = self._serial_prefix(serial)
        self._run(prefix + ["shell", "input", "swipe", "100", "500", "900", "500", "300"])

    def get_screen_size(self, serial: str) -> tuple[int, int]:
        prefix = self._serial_prefix(serial)
        result = self._run(prefix + ["shell", "wm", "size"], check=False)
        for line in result.stdout.splitlines():
            if "Physical size" in line or "Override size" in line:
                size = line.split(":")[-1].strip()
                w, h = size.split("x")
                return int(w), int(h)
        return 1080, 1920
