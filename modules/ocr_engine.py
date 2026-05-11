"""OCR engine — Claude Vision API (primary) with pytesseract fallback."""

import base64
import os
from pathlib import Path

import anthropic


_SYSTEM = (
    "You are an OCR engine. Extract all text from the book page image exactly as written, "
    "preserving paragraph breaks. Output plain text only — no commentary, no markdown formatting."
)


class OcrEngine:
    def __init__(self, api_key: str = ""):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def _encode_image(self, path: str) -> tuple[str, str]:
        """Return (base64_data, media_type)."""
        suffix = Path(path).suffix.lower()
        media_type = "image/png" if suffix == ".png" else "image/jpeg"
        with open(path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode(), media_type

    async def ocr_image(self, image_path: str) -> str:
        """Extract text from a single screenshot. Returns plain text."""
        if self._api_key:
            return await self._claude_ocr(image_path)
        return self._tesseract_ocr(image_path)

    async def _claude_ocr(self, image_path: str) -> str:
        data, media_type = self._encode_image(image_path)
        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": [{
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": data},
                }, {
                    "type": "text",
                    "text": "Extract all text from this Kindle page.",
                }],
            }],
        )
        return msg.content[0].text.strip()

    def _tesseract_ocr(self, image_path: str) -> str:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            return pytesseract.image_to_string(img, lang="jpn+eng").strip()
        except ImportError:
            return "[OCR unavailable: set ANTHROPIC_API_KEY or install pytesseract]"

    async def ocr_directory(
        self,
        image_dir: str | Path,
        progress_cb=None,
    ) -> dict[str, str]:
        """
        Run OCR on all page_*.png files in image_dir.
        Returns {filename: text} dict and saves each result as a .txt sidecar.
        progress_cb(done, total) called after each page if provided.
        """
        image_dir = Path(image_dir)
        files = sorted(image_dir.glob("page_*.png"))
        results: dict[str, str] = {}

        for i, png in enumerate(files, 1):
            txt_path = png.with_suffix(".txt")
            if txt_path.exists():
                results[png.name] = txt_path.read_text(encoding="utf-8")
            else:
                text = await self.ocr_image(str(png))
                txt_path.write_text(text, encoding="utf-8")
                results[png.name] = text
            if progress_cb:
                progress_cb(i, len(files))

        return results
