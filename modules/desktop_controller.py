"""Desktop controller — screenshot & key input via pyautogui."""

import platform
import subprocess


class DesktopController:
    def capture(self, save_path: str) -> str:
        """Take a full-screen screenshot and save to save_path."""
        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(save_path)
            return save_path
        except Exception:
            pass

        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(save_path)
            return save_path
        except Exception:
            pass

        # Linux headless fallback
        if platform.system() == "Linux":
            for cmd in [["scrot", save_path], ["gnome-screenshot", "-f", save_path]]:
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    return save_path
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue

        raise RuntimeError(
            "スクリーンショットが取得できません。pyautogui または scrot をインストールしてください。"
        )

    def press_right(self):
        """Press the right-arrow key to advance the Kindle page."""
        try:
            import pyautogui
            pyautogui.press("right")
            return
        except Exception:
            pass

        if platform.system() == "Linux":
            try:
                subprocess.run(["xdotool", "key", "Right"], check=False, capture_output=True)
                return
            except FileNotFoundError:
                pass

        raise RuntimeError(
            "キー入力が送れません。pyautogui または xdotool をインストールしてください。"
        )

    def press_left(self):
        try:
            import pyautogui
            pyautogui.press("left")
            return
        except Exception:
            pass
        if platform.system() == "Linux":
            subprocess.run(["xdotool", "key", "Left"], check=False, capture_output=True)
