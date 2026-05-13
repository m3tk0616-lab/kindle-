"""
PDF ビルダー

* PyMuPDF (fitz) が使える場合 → JPEG圧縮 + OCR テキスト埋め込み (文字検索対応)
* 使えない場合 → img2pdf でロスレス PNG 埋め込みにフォールバック

max_width=1800, jpeg_quality=85 で 11インチタブレットで十分クリアな画質。
"""

from __future__ import annotations
import io
from pathlib import Path


def build_pdf(
    image_dir: str | Path,
    output_path: str | Path | None = None,
    jpeg_quality: int = 85,
    max_width: int = 1800,
    ocr_texts: dict[str, str] | None = None,
) -> str:
    """
    image_dir 内の page_*.png を PDF にまとめる。

    Parameters
    ----------
    jpeg_quality : JPEG 品質 (1-95)。85 が圧縮と画質のバランス点。
    max_width    : PDF に埋め込む最大幅 (px)。これを超える画像はリサイズ。
    ocr_texts    : {ファイル名: テキスト} の dict。
                   渡すと PDF に不可視テキスト層を埋め込み (文字検索可能)。
    """
    try:
        import fitz  # PyMuPDF
        return _build_fitz(image_dir, output_path, jpeg_quality, max_width, ocr_texts)
    except ImportError:
        return _build_img2pdf(image_dir, output_path)


# ── PyMuPDF 実装 ─────────────────────────────────────────────────
def _build_fitz(
    image_dir: str | Path,
    output_path: str | Path | None,
    jpeg_quality: int,
    max_width: int,
    ocr_texts: dict[str, str] | None,
) -> str:
    import fitz
    from PIL import Image

    image_dir = Path(image_dir)
    if output_path is None:
        suffix = "_ocr" if ocr_texts else ""
        output_path = image_dir / f"output{suffix}.pdf"
    output_path = Path(output_path)

    png_files = sorted(image_dir.glob("page_*.png"))
    if not png_files:
        raise FileNotFoundError(f"page_*.png が見つかりません: {image_dir}")

    doc = fitz.open()

    for png_path in png_files:
        img = Image.open(png_path).convert("RGB")
        w, h = img.size

        # 大きすぎる画像をリサイズ (画質優先で LANCZOS)
        if w > max_width:
            ratio = max_width / w
            img = img.resize((max_width, int(h * ratio)), Image.LANCZOS)
            w, h = img.size

        # JPEG へ変換
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=jpeg_quality, optimize=True, subsampling=0)
        jpeg_bytes = buf.getvalue()

        # PDF ページサイズ (pt) — 150 DPI 相当
        # pt = px / dpi * 72   →  150 DPI なら pt = px * 0.48
        DPI = 150
        w_pt = w / DPI * 72
        h_pt = h / DPI * 72

        page = doc.new_page(width=w_pt, height=h_pt)
        rect = fitz.Rect(0, 0, w_pt, h_pt)
        page.insert_image(rect, stream=jpeg_bytes, keep_proportion=False)

        # OCR テキスト埋め込み (不可視テキスト層)
        text = (ocr_texts or {}).get(png_path.name, "").strip()
        if text:
            # font size 1pt, white → 見えないが PDF 内テキスト検索可能
            page.insert_text(
                fitz.Point(0, h_pt - 2),
                text,
                fontsize=1,
                color=(1.0, 1.0, 1.0),
                overlay=False,
            )

    # deflate=True: PDF 内部圧縮  garbage=4: 不要オブジェクト削除
    doc.save(str(output_path), deflate=True, garbage=4, linear=True)
    doc.close()
    return str(output_path)


# ── img2pdf フォールバック (PyMuPDF なし) ─────────────────────────
def _build_img2pdf(
    image_dir: str | Path,
    output_path: str | Path | None,
) -> str:
    import img2pdf

    image_dir = Path(image_dir)
    if output_path is None:
        output_path = image_dir / "output.pdf"
    output_path = Path(output_path)

    png_files = sorted(image_dir.glob("page_*.png"))
    if not png_files:
        raise FileNotFoundError(f"page_*.png が見つかりません: {image_dir}")

    with open(output_path, "wb") as f:
        f.write(img2pdf.convert([str(p) for p in png_files]))

    return str(output_path)


def get_pdf_info(pdf_path: str | Path) -> dict:
    path = Path(pdf_path)
    if not path.exists():
        return {"exists": False}
    size_mb = round(path.stat().st_size / (1024 * 1024), 2)
    return {"exists": True, "path": str(path), "size_mb": size_mb}
