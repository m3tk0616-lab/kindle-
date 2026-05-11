"""Android ADB controller — screenshot & page-turn via adb shell."""

import subprocess
from pathlib import Path
from PIL import Image


class AdbController:
    # Cache screen sizes per serial to avoid repeated adb calls
    _size_cache: dict[str, tuple[int, int]] = {}

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
        """Take a lossless PNG screenshot at native resolution and pull to save_path."""
        remote = "/data/local/tmp/_kindle_ss.png"
        prefix = self._serial_prefix(serial)
        self._run(prefix + ["shell", "screencap", "-p", remote])
        self._run(prefix + ["pull", remote, save_path])
        # Re-save with Pillow to strip any metadata and guarantee lossless PNG
        img = Image.open(save_path)
        img.save(save_path, format="PNG", optimize=False, compress_level=1)
        return save_path

    def get_image_info(self, save_path: str) -> dict:
        """Return width, height, and file size of a saved screenshot."""
        img = Image.open(save_path)
        size_kb = Path(save_path).stat().st_size // 1024
        return {"width": img.width, "height": img.height, "size_kb": size_kb}

    def tap(self, serial: str, x: int, y: int):
        prefix = self._serial_prefix(serial)
        self._run(prefix + ["shell", "input", "tap", str(x), str(y)])

    def swipe_next_page(self, serial: str):
        """Swipe left to advance the Kindle page, using actual screen dimensions."""
        w, h = self.get_screen_size(serial)
        cx = h // 2  # vertical center (handles portrait/landscape)
        prefix = self._serial_prefix(serial)
        # from 80% width → 20% width, at vertical center
        x_start = int(w * 0.8)
        x_end   = int(w * 0.2)
        y_mid   = h // 2
        self._run(prefix + ["shell", "input", "swipe",
                             str(x_start), str(y_mid), str(x_end), str(y_mid), "300"])

    def swipe_prev_page(self, serial: str):
        w, h = self.get_screen_size(serial)
        prefix = self._serial_prefix(serial)
        x_start = int(w * 0.2)
        x_end   = int(w * 0.8)
        y_mid   = h // 2
        self._run(prefix + ["shell", "input", "swipe",
                             str(x_start), str(y_mid), str(x_end), str(y_mid), "300"])

    def get_screen_size(self, serial: str) -> tuple[int, int]:
        key = serial or "__default__"
        if key in self._size_cache:
            return self._size_cache[key]
        prefix = self._serial_prefix(serial)
        result = self._run(prefix + ["shell", "wm", "size"], check=False)
        for line in result.stdout.splitlines():
            if "Physical size" in line or "Override size" in line:
                size = line.split(":")[-1].strip()
                w, h = size.split("x")
                self._size_cache[key] = (int(w), int(h))
                return self._size_cache[key]
        return 1080, 1920
