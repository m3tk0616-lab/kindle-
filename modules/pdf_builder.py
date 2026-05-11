"""Build a PDF from a directory of PNG screenshots."""

import os
from pathlib import Path

import img2pdf
from PIL import Image


def build_pdf(image_dir: str | Path, output_path: str | Path | None = None) -> str:
    """
    Collect all page_*.png files in image_dir (sorted), embed them losslessly
    into a PDF, and return the path to the generated file.
    """
    image_dir = Path(image_dir)
    if output_path is None:
        output_path = image_dir / "output.pdf"
    output_path = Path(output_path)

    png_files = sorted(image_dir.glob("page_*.png"))
    if not png_files:
        raise FileNotFoundError(f"No page_*.png files found in {image_dir}")

    # img2pdf embeds PNGs as-is (lossless), no re-encoding
    with open(output_path, "wb") as f:
        f.write(img2pdf.convert([str(p) for p in png_files]))

    return str(output_path)


def get_pdf_info(pdf_path: str | Path) -> dict:
    path = Path(pdf_path)
    if not path.exists():
        return {"exists": False}
    size_mb = round(path.stat().st_size / (1024 * 1024), 2)
    return {"exists": True, "path": str(path), "size_mb": size_mb}
