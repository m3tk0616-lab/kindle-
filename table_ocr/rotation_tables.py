"""
表画像（指揮訓練ローテーション表・図上表など）→ 整形済みPDF 自動化スクリプト

処理の流れ
  1. 向き補正（EXIF → Tesseract OSD）・用紙/表領域の自動クロップ・傾き補正
  2. 罫線検出でセル構造（結合セル含む）を復元し、セル単位でOCR
  3. JSON / Markdown / HTML（ゴシック体）に整形
  4. Chromium（Playwright）で 1 画像 = 1 ページの PDF を出力

使い方
  python rotation_tables.py input/ -o output/rotation_tables.pdf
  # OCR結果（output/*.json）を手で直した後、OCRせずに再レンダリング:
  python rotation_tables.py --from-json output/ -o output/rotation_tables.pdf

外部送信は一切行いません（OCR・PDF化はすべてローカル処理）。
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
FONT_STACK = '"Noto Sans CJK JP", "Noto Sans JP", "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", sans-serif'
CJK = r"\u3000-\u30ff\u3400-\u9fff\uff00-\uffef々〆〇"


# ── 1. 画像の向き補正・クロップ ──────────────────────────────────

def load_image(path: Path) -> np.ndarray:
    pil = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def rotate90(img: np.ndarray, deg: int) -> np.ndarray:
    deg %= 360
    codes = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return cv2.rotate(img, codes[deg]) if deg else img


def ocr_score(img: np.ndarray) -> float:
    """向き判定用: 日本語OCRの平均信頼度 × 認識文字数"""
    small = resize_max(img, 1400)
    d = pytesseract.image_to_data(small, lang="jpn", config="--psm 6", output_type=pytesseract.Output.DICT)
    confs = [float(c) for c, t in zip(d["conf"], d["text"]) if t.strip() and float(c) > 0]
    return (sum(confs) / len(confs)) * len(confs) ** 0.5 if confs else 0.0


def fix_orientation(img: np.ndarray) -> tuple[np.ndarray, int]:
    """4方向に回転させて日本語OCRの信頼度が最も高い向きを採用（文字が正位置になる向き）
    ※ Tesseract OSD は日本語では機能しないため使わない"""
    scores = {d: ocr_score(rotate90(img, d)) for d in (0, 90, 180, 270)}
    deg = max(scores, key=scores.get)
    return rotate90(img, deg), deg


def resize_max(img: np.ndarray, side: int) -> np.ndarray:
    h, w = img.shape[:2]
    s = side / max(h, w)
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else img


def order_quad(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(4, 2).astype(np.float32)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]], np.float32)


def crop_paper(img: np.ndarray) -> np.ndarray:
    """背景（机など）から用紙を切り出し、四隅が取れれば透視変換で正面化"""
    small = resize_max(img, 1200)
    k = img.shape[1] / small.shape[1]
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    # 用紙 = 低彩度・高明度。木目など有彩色の背景を除外する
    mask = cv2.inRange(hsv, (0, 0, 120), (180, 70, 255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return img
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 0.15 * small.shape[0] * small.shape[1]:
        return img
    hull = cv2.convexHull(c)
    approx = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True)
    if len(approx) == 4:
        q = order_quad(approx) * k
        w = int(max(np.linalg.norm(q[0] - q[1]), np.linalg.norm(q[3] - q[2])))
        h = int(max(np.linalg.norm(q[0] - q[3]), np.linalg.norm(q[1] - q[2])))
        dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float32)
        return cv2.warpPerspective(img, cv2.getPerspectiveTransform(q, dst), (w, h))
    x, y, w, h = (np.array(cv2.boundingRect(hull)) * k).astype(int)
    return img[y:y + h, x:x + w]


def binarize(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 35, 15)


def line_masks(binary: np.ndarray, min_v: int = 0) -> tuple[np.ndarray, np.ndarray]:
    h, w = binary.shape
    # 文字の画（漢字の横棒など）を罫線と誤認しないよう、幅/高さの 1/12 以上続く線だけを残す
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, w // 12), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, h // 12, min_v)))
    hm = cv2.dilate(cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk), np.ones((3, 3), np.uint8))
    vm = cv2.dilate(cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk), np.ones((3, 3), np.uint8))
    return hm, vm


def deskew(img: np.ndarray) -> np.ndarray:
    """横罫線の角度から微小な傾きを補正"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hm, _ = line_masks(binarize(gray))
    lines = cv2.HoughLinesP(hm, 1, np.pi / 720, 200, minLineLength=img.shape[1] // 4, maxLineGap=20)
    if lines is None:
        return img
    angles = [np.degrees(np.arctan2(y2 - y1, x2 - x1)) for x1, y1, x2, y2 in lines.reshape(-1, 4)]
    angles = [a for a in angles if abs(a) < 10]
    if not angles:
        return img
    a = float(np.median(angles))
    if abs(a) < 0.15:
        return img
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), a, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def table_bbox(img: np.ndarray) -> tuple[int, int, int, int] | None:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hm, vm = line_masks(binarize(gray))
    grid = cv2.dilate(cv2.bitwise_or(hm, vm), np.ones((7, 7), np.uint8))
    cnts, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    x, y, w, h = cv2.boundingRect(max(cnts, key=cv2.contourArea))
    if w * h < 0.1 * img.shape[0] * img.shape[1]:
        return None
    return x, y, w, h


def preprocess(path: Path, margin: int = 24) -> tuple[np.ndarray, np.ndarray | None, int]:
    """戻り値: (表本体の画像, 表の上にある見出し領域の画像, 回転角)"""
    img = crop_paper(load_image(path))  # 背景を除いてから向きを判定する（木目がOCR判定を乱すため）
    img, deg = fix_orientation(img)
    img = deskew(img)
    bb = table_bbox(img)
    if not bb:
        return img, None, deg
    x, y, w, h = bb
    H, W = img.shape[:2]
    table = img[max(0, y - margin):min(H, y + h + margin), max(0, x - margin):min(W, x + w + margin)]
    if table.shape[1] < 1600:  # 低解像度はOCR精度が落ちるので拡大
        table = cv2.resize(table, None, fx=1600 / table.shape[1], fy=1600 / table.shape[1], interpolation=cv2.INTER_CUBIC)
    header = img[:max(0, y - 4), max(0, x - margin):min(W, x + w + margin)] if y > 40 else None
    return table, header, deg


# ── 2. 罫線からセル構造を復元してOCR ─────────────────────────────

def peaks(profile: np.ndarray, thresh: float, min_gap: int) -> list[int]:
    idx = np.where(profile >= thresh)[0]
    if idx.size == 0:
        return []
    groups, cur = [], [idx[0]]
    for i in idx[1:]:
        if i - cur[-1] <= min_gap:
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)
    return [int(np.mean(g)) for g in groups]


def clean_text(t: str) -> str:
    t = re.sub(rf"(?<=[{CJK}0-9A-Za-z])\s+(?=[{CJK}])|(?<=[{CJK}])\s+(?=[0-9A-Za-z])", "", t)  # 日本語文字間の余計な空白
    t = re.sub(r"(?<=[0-9])\s*[・･.]\s*(?=[0-9]{2}\b)", ":", t)                        # 9・30 → 9:30
    t = re.sub(r"^[-ー_—~〜.,・\s]+(?=\S)|[。、.,・]+$", "", t.strip())                  # 先頭・末尾のノイズ
    t = re.sub(r"(?<![0-9])\s*[:：;]\s*|\s*[:：;]\s*(?![0-9])", " ", t)                   # 時刻以外のコロン
    t = re.sub(r"[|｜]{1,}$|^[|｜]+", "", t.strip())       # 罫線の誤認識
    return re.sub(r"\s+", " ", t).strip()


def ocr_cell(img: np.ndarray) -> tuple[str, float]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    if gray.size == 0 or (binarize(gray) > 0).mean() < 0.004:
        return "", 100.0
    scale = max(1.0, 60 / max(1, gray.shape[0])) if gray.shape[0] < 60 else 1.0
    if scale > 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.copyMakeBorder(gray, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)

    def run(lang: str, psm: int) -> tuple[str, float]:
        d = pytesseract.image_to_data(gray, lang=lang, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
        lines: dict[tuple, list[str]] = {}
        confs = []
        for i, t in enumerate(d["text"]):
            if t.strip() and float(d["conf"][i]) >= 0:
                lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(t)
                confs.append(float(d["conf"][i]))
        text = "\n".join(clean_text(" ".join(v)) for v in lines.values())
        return text.strip(), (sum(confs) / len(confs) if confs else 0.0)

    best = run("jpn", 6)
    if gray.shape[1] > gray.shape[0] * 1.5:  # 1行のセル → 単一行モードも試す
        alt = run("jpn", 7)
        if alt[0] and alt[1] > best[1]:
            best = alt
    if gray.shape[0] > gray.shape[1] * 1.8:  # 縦長セル → 縦書きも試す
        alt = run("jpn_vert", 5)
        if alt[1] > best[1]:
            best = alt
    return best


def extract_table(img: np.ndarray) -> dict:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = binarize(gray)
    hm, vm = line_masks(binary)
    H, W = gray.shape
    ys = peaks(hm.sum(1) / 255, 0.12 * W, max(6, int(H * 0.015)))  # 二重線・太線は1本にまとめる
    if len(ys) >= 2:  # 縦罫線は「行の高さの7割以上」続くものに限定（行数が少ない表で文字の縦画を除外）
        hm, vm = line_masks(binary, int(0.7 * min(np.diff(ys))))
    xs = peaks(vm.sum(0) / 255, 0.12 * H, max(6, int(W * 0.015)))
    if len(ys) < 2 or len(xs) < 2:
        return extract_lines_fallback(img)

    R, C = len(ys) - 1, len(xs) - 1
    parent = list(range(R * C))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent[find(a)] = find(b)

    band = 4
    for r in range(R):
        for c in range(C):
            y0, y1, x0, x1 = ys[r], ys[r + 1], xs[c], xs[c + 1]
            # 右側の縦罫線が途切れている → 横方向に結合
            if c + 1 < C:
                seg = vm[y0 + band:y1 - band, max(0, x1 - band):x1 + band]
                if seg.size and (seg.max(1) > 0).mean() < 0.5:
                    union(r * C + c, r * C + c + 1)
            # 下側の横罫線が途切れている → 縦方向に結合
            if r + 1 < R:
                seg = hm[max(0, y1 - band):y1 + band, x0 + band:x1 - band]
                if seg.size and (seg.max(0) > 0).mean() < 0.5:
                    union(r * C + c, (r + 1) * C + c)

    groups: dict[int, list[tuple[int, int]]] = {}
    for r in range(R):
        for c in range(C):
            groups.setdefault(find(r * C + c), []).append((r, c))

    ink = cv2.bitwise_and(binary, cv2.bitwise_not(cv2.bitwise_or(hm, vm)))
    clean = cv2.bitwise_not(ink)  # 罫線を除去した白地黒文字
    cells = []
    for members in groups.values():
        r0, r1 = min(m[0] for m in members), max(m[0] for m in members)
        c0, c1 = min(m[1] for m in members), max(m[1] for m in members)
        pad = 3
        crop = clean[ys[r0] + pad:ys[r1 + 1] - pad, xs[c0] + pad:xs[c1 + 1] - pad]
        text, conf = ocr_cell(crop)
        cells.append({"row": r0, "col": c0, "rowspan": r1 - r0 + 1, "colspan": c1 - c0 + 1,
                      "text": text, "conf": round(conf, 1)})
    cells.sort(key=lambda c: (c["row"], c["col"]))
    col_w = [round((xs[i + 1] - xs[i]) / (xs[-1] - xs[0]), 4) for i in range(C)]
    return {"rows": R, "cols": C, "col_widths": col_w, "cells": cells}


def extract_lines_fallback(img: np.ndarray) -> dict:
    """罫線が取れない場合: 行ごとにOCRし、大きな空白で列を区切る"""
    d = pytesseract.image_to_data(img, lang="jpn+eng", config="--psm 6", output_type=pytesseract.Output.DICT)
    lines: dict[tuple, list[int]] = {}
    for i, t in enumerate(d["text"]):
        if t.strip():
            lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append(i)
    rows = []
    for idxs in lines.values():
        idxs.sort(key=lambda i: d["left"][i])
        h = np.median([d["height"][i] for i in idxs])
        row, cur, prev_r = [], [], None
        for i in idxs:
            if prev_r is not None and d["left"][i] - prev_r > 1.5 * h:
                row.append(clean_text(" ".join(d["text"][j] for j in cur)))
                cur = []
            cur.append(i)
            prev_r = d["left"][i] + d["width"][i]
        row.append(clean_text(" ".join(d["text"][j] for j in cur)))
        rows.append(row)
    C = max((len(r) for r in rows), default=1)
    cells = [{"row": r, "col": c, "rowspan": 1, "colspan": 1, "text": t, "conf": 0.0}
             for r, row in enumerate(rows) for c, t in enumerate(row + [""] * (C - len(row)))]
    return {"rows": len(rows), "cols": C, "col_widths": [round(1 / C, 4)] * C, "cells": cells}


# ── 3. Markdown / HTML 整形 ───────────────────────────────────────

def to_grid(table: dict) -> list[list[str]]:
    grid = [[""] * table["cols"] for _ in range(table["rows"])]
    for c in table["cells"]:
        for r in range(c["row"], c["row"] + c["rowspan"]):
            for k in range(c["col"], c["col"] + c["colspan"]):
                grid[r][k] = c["text"] if (r, k) == (c["row"], c["col"]) else "〃"
    return grid


def to_markdown(doc: dict) -> str:
    grid = to_grid(doc["table"])
    esc = lambda s: s.replace("|", "\\|").replace("\n", "<br>")
    out = [f"## {doc['title']}", ""]
    if grid:
        out.append("| " + " | ".join(esc(s) for s in grid[0]) + " |")
        out.append("|" + "---|" * len(grid[0]))
        out += ["| " + " | ".join(esc(s) for s in row) + " |" for row in grid[1:]]
    return "\n".join(out) + "\n"


def table_html(doc: dict, review: bool) -> str:
    """任意キー（JSON を手で直すとき用）:
       table.header_rows / header_cols … 見出し扱いにする先頭の行数・列数（既定 1）
       table.shade_cols                … 網掛けする列（例: 2班の列）
       cell.vertical                   … 縦書き（区分ラベルなど）
       cell.na                         … 斜線セル（該当なし）
       cell.note                       … 小さな注記（「兼務」など）"""
    t = doc["table"]
    hr, hc = t.get("header_rows", 1), t.get("header_cols", 1)
    shade = set(t.get("shade_cols", []))
    by_pos = {(c["row"], c["col"]): c for c in t["cells"]}
    covered = set()
    for c in t["cells"]:
        for r in range(c["row"], c["row"] + c["rowspan"]):
            for k in range(c["col"], c["col"] + c["colspan"]):
                if (r, k) != (c["row"], c["col"]):
                    covered.add((r, k))
    cols = "".join(f'<col style="width:{w * 100:.2f}%">' for w in t["col_widths"])
    rows = []
    for r in range(t["rows"]):
        tds = []
        for k in range(t["cols"]):
            if (r, k) in covered:
                continue
            c = by_pos.get((r, k), {"text": "", "rowspan": 1, "colspan": 1, "conf": 100})
            tag = "th" if r < hr or k < hc else "td"
            attrs, cls = "", []
            if c.get("rowspan", 1) > 1:
                attrs += f' rowspan="{c["rowspan"]}"'
            if c.get("colspan", 1) > 1:
                attrs += f' colspan="{c["colspan"]}"'
            if k in shade and c.get("colspan", 1) == 1:
                cls.append("shade")
            if c.get("vertical"):
                cls.append("vert")
            if c.get("na"):
                cls.append("na")
            if review and c["text"] and c.get("conf", 100) < 70:
                cls.append("low")
                attrs += f' title="信頼度 {c["conf"]}"'
            if cls:
                attrs += f' class="{" ".join(cls)}"'
            body = html.escape(c["text"]).replace(chr(10), "<br>")
            if c.get("note"):
                body += f'<span class="note">{html.escape(c["note"])}</span>'
            tds.append(f"<{tag}{attrs}>{body}</{tag}>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f'<table><colgroup>{cols}</colgroup>{"".join(rows)}</table>'


def build_html(docs: list[dict], review: bool = False) -> str:
    pages, orients = [], []
    for d in docs:
        orient = d.get("orientation") or ("landscape" if d["table"]["cols"] >= 10 and d["table"]["cols"] > d["table"]["rows"] else "portrait")
        # 行・列が少ない表は大きく、多い表は小さく（はみ出す場合は下の JS がさらに縮小）
        fs = max(8.0, min(14.0, 110 / d["table"]["cols"], 260 / max(1, d["table"]["rows"])))
        fs = d.get("font_pt", fs)
        orients.append(orient)
        meta = "".join(f"<p>{html.escape(x)}</p>" for x in d.get("subtitle", []))
        meta = f'<div class="meta">{meta}</div>' if meta else ""
        pages.append(f'<section class="page {orient}" style="font-size:{fs:.1f}pt"><div class="fit"><h1>{html.escape(d["title"])}</h1>'
                     f'{meta}{table_html(d, review)}</div></section>')
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>ローテーション表</title>
<style>
  /* 既定ページ幅が狭いと Chromium が全体を縮小してしまうため、最初の表の向きに合わせる */
  @page {{ size: A4 {orients[0] if orients else "portrait"}; margin: 12mm; }}
  @page portrait {{ size: A4 portrait; margin: 12mm; }}
  @page landscape {{ size: A4 landscape; margin: 12mm; }}
  html, body {{ margin: 0; background: #fff; color: #111; font-family: {FONT_STACK}; }}
  .page {{ break-after: page; overflow: hidden; }}
  .page:last-child {{ break-after: auto; }}
  .portrait {{ page: portrait; width: 186mm; height: 272mm; }}
  .landscape {{ page: landscape; width: 273mm; height: 185mm; }}
  .fit {{ transform-origin: top left; }}
  h1 {{ font-size: 16pt; font-weight: 700; margin: 0 0 4mm; padding-bottom: 2mm;
        border-bottom: 2px solid #1f3a5f; color: #1f3a5f; }}
  table {{ width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 1em; }}
  th, td {{ border: 0.8px solid #555; padding: 0.6em 0.4em; text-align: center; vertical-align: middle;
           word-break: break-all; line-height: 1.35; }}
  th {{ background: #e8eef6; font-weight: 700; }}
  .meta {{ display: flex; flex-wrap: wrap; gap: 0 6mm; margin: -2mm 0 3mm; font-size: 9pt; color: #333; }}
  .meta p {{ margin: 0; }}
  td.shade {{ background: #e3e9f3; }}
  th.shade {{ background: #c9d5e8; }}
  th.vert {{ writing-mode: vertical-rl; text-orientation: upright; letter-spacing: 0.15em; padding: 0.3em 0; }}
  td.na {{ background: linear-gradient(to top right, transparent calc(50% - 0.5px), #555 50%, transparent calc(50% + 0.5px)); }}
  .note {{ display: block; font-size: 0.75em; color: #444; margin-top: 0.15em; }}
  td.low, th.low {{ background: #fff3b0 !important; outline: 1px dashed #c90; }}
</style></head><body>
{''.join(pages)}
<script>
  // 1 表 = 1 ページに収まるよう縮小
  document.querySelectorAll('.page').forEach(p => {{
    const f = p.querySelector('.fit');
    const s = Math.min(1, p.clientHeight / f.scrollHeight, p.clientWidth / f.scrollWidth);
    if (s < 1) {{ f.style.transform = 'scale(' + s + ')'; f.style.width = (100 / s) + '%'; }}
  }});
</script>
</body></html>"""


# ── 4. PDF 変換 ───────────────────────────────────────────────────

def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True)
        browser.close()


# ── main ──────────────────────────────────────────────────────────

def process_image(path: Path, out_dir: Path, title: str | None) -> dict:
    table_img, header_img, deg = preprocess(path)
    cv2.imwrite(str(out_dir / f"{path.stem}_corrected.png"), table_img)
    if not title and header_img is not None and header_img.size:
        g = cv2.cvtColor(header_img, cv2.COLOR_BGR2GRAY)
        title = clean_text(pytesseract.image_to_string(g, lang="jpn", config="--psm 6")).split("\n")[0]
    doc = {"source": path.name, "rotation": deg, "title": title or path.stem, "table": extract_table(table_img)}
    (out_dir / f"{path.stem}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), "utf-8")
    (out_dir / f"{path.stem}.md").write_text(to_markdown(doc), "utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="表画像を補正・OCRしてゴシック体の整形PDFを出力")
    ap.add_argument("input", type=Path, help="画像フォルダ（--from-json 時は JSON フォルダ）")
    ap.add_argument("-o", "--output", type=Path, default=Path("output/rotation_tables.pdf"))
    ap.add_argument("--titles", nargs="*", help="各ページの見出し（画像のファイル名順）")
    ap.add_argument("--from-json", action="store_true", help="OCRせず、修正済み JSON から再レンダリング")
    args = ap.parse_args()

    out_dir = args.output.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.from_json:
        docs = [json.loads(p.read_text("utf-8")) for p in sorted(args.input.glob("*.json"))]
    else:
        images = sorted(p for p in args.input.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if not images:
            print(f"画像が見つかりません: {args.input}", file=sys.stderr)
            return 1
        docs = []
        for i, p in enumerate(images):
            title = args.titles[i] if args.titles and i < len(args.titles) else None
            print(f"[{i + 1}/{len(images)}] {p.name} を処理中…")
            d = process_image(p, out_dir, title)
            t = d["table"]
            low = sum(1 for c in t["cells"] if c["text"] and c["conf"] < 70)
            print(f"    回転 {d['rotation']}° / {t['rows']}行 × {t['cols']}列 / 要確認セル {low}")
            docs.append(d)
    if not docs:
        print("処理対象がありません", file=sys.stderr)
        return 1

    html_path = args.output.with_suffix(".html")
    html_path.write_text(build_html(docs), "utf-8")
    (out_dir / "review.html").write_text(build_html(docs, review=True), "utf-8")
    (out_dir / "rotation_tables.md").write_text("\n".join(to_markdown(d) for d in docs), "utf-8")
    html_to_pdf(html_path, args.output)
    print(f"PDF を出力しました: {args.output}（{len(docs)} ページ）")
    print(f"要確認セルの黄色表示: {out_dir / 'review.html'}  ／  修正は {out_dir}/*.json → --from-json で再出力")
    return 0


if __name__ == "__main__":
    sys.exit(main())
