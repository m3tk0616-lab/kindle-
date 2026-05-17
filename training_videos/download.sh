#!/bin/bash
# トレーニング動画一括ダウンロードスクリプト
# 使い方: bash download.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Day1 動画ダウンロード開始 (17本) ==="
yt-dlp -a "$SCRIPT_DIR/day1/urls.txt" \
  -o "$SCRIPT_DIR/day1/%(title)s.%(ext)s" \
  --no-playlist

echo ""
echo "=== Day2 動画ダウンロード開始 (29本) ==="
yt-dlp -a "$SCRIPT_DIR/day2/urls.txt" \
  -o "$SCRIPT_DIR/day2/%(title)s.%(ext)s" \
  --no-playlist

echo ""
echo "=== 完了 ==="
