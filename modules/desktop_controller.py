"""Desktop controller — screenshot & key input via pyautogui."""

import platform
import subprocess

try:
    import pyautogui
    _PYAUTOGUI = True
except Exception:
    _PYAUTOGUI = False

try:
    from PIL import ImageGrab
    _PIL = True
except Exception:
    _PIL = False


class DesktopController:
    def capture(self, save_path: str) -> str:
        """Take a full-screen screenshot and save to save_path."""
        if _PYAUTOGUI:
            img = pyautogui.screenshot()
            img.save(save_path)
        elif _PIL:
            img = ImageGrab.grab()
            img.save(save_path)
        else:
            # Linux fallback via scrot / gnome-screenshot
            system = platform.system()
            if system == "Linux":
                try:
                    subprocess.run(["scrot", save_path], check=True)
                except FileNotFoundError:
                    subprocess.run(["gnome-screenshot", "-f", save_path], check=True)
            else:
                raise RuntimeError("pyautogui not available and no fallback found")
        return save_path

    def press_right(self):
        """Press the right-arrow key to advance the Kindle page."""
        if _PYAUTOGUI:
            pyautogui.press("right")
        else:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdotool", "key", "Right"], check=False)
            else:
                raise RuntimeError("pyautogui not available")

    def press_left(self):
        if _PYAUTOGUI:
            pyautogui.press("left")
        else:
            system = platform.system()
            if system == "Linux":
                subprocess.run(["xdotool", "key", "Left"], check=False)
