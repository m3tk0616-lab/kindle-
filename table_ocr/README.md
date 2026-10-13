# 表画像 → 整形PDF 自動化（指揮訓練ローテーション表・図上表）

スマホで撮影した表の画像を、向き補正・クロップ・OCR したうえで、ゴシック体（Noto Sans CJK JP など）の
見やすい表として PDF に出力します（1 画像 = 1 ページ）。**処理はすべてローカルで完結し、外部 API には送信しません。**

## セットアップ

```bash
# Tesseract（OCRエンジン）と日本語データ、Noto CJK フォント
sudo apt-get install -y tesseract-ocr tesseract-ocr-jpn tesseract-ocr-jpn-vert fonts-noto-cjk
#   Windows: https://github.com/UB-Mannheim/tesseract/wiki のインストーラで「Japanese」を追加
#   macOS:   brew install tesseract tesseract-lang
pip install -r requirements.txt
playwright install chromium   # PDF 変換用ブラウザ（初回のみ）
```

## 使い方

```bash
# 1) input/ に画像（jpg/png 等）を置いて実行
python rotation_tables.py input/ -o output/rotation_tables.pdf

# ページ見出しを指定したい場合（ファイル名順）
python rotation_tables.py input/ -o output/rotation_tables.pdf --titles "指揮訓練ローテーション表" "図上表"

# 2) OCR結果を手直しして再出力（OCRはやり直さない）
#    output/review.html で黄色のセル（信頼度 70 未満）を確認 → output/<画像名>.json の "text" を修正
python rotation_tables.py --from-json output/ -o output/rotation_tables.pdf
```

## 処理内容

| 段階 | 内容 |
|---|---|
| 1. 回転・クロップ | EXIF 補正 → 低彩度・高明度領域から用紙を検出し透視変換（机の木目などを除去）→ 4方向で日本語OCR信頼度を比較して文字が正位置になる向きに回転 → 横罫線の角度で傾き補正 → 罫線の外接矩形で表を切り出し |
| 2. OCR | 罫線を検出して行・列を復元（途切れた罫線から結合セルも判定）→ 罫線を消してセルごとに Tesseract（jpn / 縦長セルは jpn_vert も試行）|
| 3. 整形 | `<画像名>.json`（セル・結合・信頼度）、`rotation_tables.md`、HTML（ゴシック体） |
| 4. PDF | Chromium で A4 出力。列が多い表は自動で横向き、はみ出す場合は自動縮小 |

## 出力ファイル（`output/`）

- `rotation_tables.pdf` … 最終PDF
- `rotation_tables.html` / `rotation_tables.md` … 整形済みの表
- `review.html` … 要確認セルを黄色表示した確認用
- `<画像名>.json` … 手修正用データ（`--from-json` で再レンダリング）
- `<画像名>_corrected.png` … 回転・クロップ後の画像

## 注意

手書き文字は Tesseract では誤読が多くなります。印刷文字・表構造はおおむね自動で取れますが、
人名などの手書き部分は `review.html` で確認し JSON を修正してから `--from-json` で出力してください。
