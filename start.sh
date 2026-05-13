#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Install dependencies if not already done
if [ ! -f ".deps_installed" ]; then
    echo "依存ライブラリをインストールしています..."
    pip install -r requirements.txt
    touch .deps_installed
fi

# Open browser (Mac / Linux)
if command -v open &>/dev/null; then
    (sleep 2 && open http://localhost:8000) &
elif command -v xdg-open &>/dev/null; then
    (sleep 2 && xdg-open http://localhost:8000) &
fi

echo ""
echo "========================================"
echo "  Kindle Auto Capture 起動中..."
echo "  ブラウザで http://localhost:8000 を開いてください"
echo "  終了するには Ctrl+C を押してください"
echo "========================================"
echo ""

python -m uvicorn main:app --host 0.0.0.0 --port 8000
