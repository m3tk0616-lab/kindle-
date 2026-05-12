"""Android ADB controller — screenshot & page-turn via adb shell."""

import subprocess
import sys
from pathlib import Path


class AdbNotFoundError(RuntimeError):
    pass


def _adb_bin() -> str:
    """
    bin/adb.exe (setup.bat でダウンロード済み) を優先して使う。
    なければ PATH 上の adb を使う。
    """
    # exe と同階層か、その親の bin/ を探す
    for base in (Path(sys.executable).parent, Path(__file__).parent.parent):
        candidate = base / "bin" / "adb.exe"
        if candidate.exists():
            return str(candidate)
    return "adb"


class AdbController:
    _size_cache: dict[str, tuple[int, int]] = {}
    _adb = _adb_bin()

    def _run(self, args: list[str], check=True) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                [self._adb] + args,
                capture_output=True,
                text=True,
                check=check,
            )
        except FileNotFoundError:
            raise AdbNotFoundError(
                "adb が見つかりません。setup.bat を実行してください。"
            )

    def _serial_prefix(self, serial: str) -> list[str]:
        return ["-s", serial] if serial else []

    def list_devices(self) -> list[dict]:
        try:
            result = self._run(["devices", "-l"], check=False)
        except AdbNotFoundError:
            return []
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

    def capture(self, serial: str, save_path: str,
                crop: tuple[int, int, int, int] | None = None) -> str:
        """
        Take a lossless PNG screenshot.
        crop=(x1,y1,x2,y2) in device pixels crops the image after capture.
        """
        from PIL import Image
        remote = "/data/local/tmp/_kindle_ss.png"
        prefix = self._serial_prefix(serial)
        self._run(prefix + ["shell", "screencap", "-p", remote])
        self._run(prefix + ["pull", remote, save_path])
        img = Image.open(save_path)
        if crop:
            x1, y1, x2, y2 = crop
            img = img.crop((x1, y1, x2, y2))
        img.save(save_path, format="PNG", optimize=False, compress_level=1)
        return save_path

    def get_image_info(self, save_path: str) -> dict:
        from PIL import Image
        img = Image.open(save_path)
        size_kb = Path(save_path).stat().st_size // 1024
        return {"width": img.width, "height": img.height, "size_kb": size_kb}

    def tap(self, serial: str, x: int, y: int):
        prefix = self._serial_prefix(serial)
        self._run(prefix + ["shell", "input", "tap", str(x), str(y)])

    def swipe_next_page(self, serial: str):
        w, h = self.get_screen_size(serial)
        prefix = self._serial_prefix(serial)
        x_start, x_end, y_mid = int(w * 0.8), int(w * 0.2), h // 2
        self._run(prefix + ["shell", "input", "swipe",
                             str(x_start), str(y_mid), str(x_end), str(y_mid), "300"])

    def swipe_prev_page(self, serial: str):
        w, h = self.get_screen_size(serial)
        prefix = self._serial_prefix(serial)
        x_start, x_end, y_mid = int(w * 0.2), int(w * 0.8), h // 2
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
