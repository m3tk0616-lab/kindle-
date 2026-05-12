@echo off
title Kindle Auto Capture — ビルド
cd /d "%~dp0"

echo ========================================
echo   依存ライブラリをインストールしています...
echo ========================================
pip install Pillow imagehash img2pdf PyMuPDF anthropic sse-starlette pyinstaller -q
if errorlevel 1 ( echo インストール失敗 & pause & exit /b 1 )

echo.
echo ========================================
echo   .exe を作成しています（数分かかります）
echo ========================================
pyinstaller --onefile --windowed --name "KindleAutoCapture" ^
  --add-data "modules;modules" ^
  --add-data "static;static" ^
  --hidden-import=PIL._tkinter_finder ^
  --hidden-import=imagehash ^
  --hidden-import=img2pdf ^
  --hidden-import=fitz ^
  --hidden-import=anthropic ^
  --icon=static\icon-512.png ^
  app_gui.py

if errorlevel 1 ( echo ビルド失敗 & pause & exit /b 1 )

echo.
echo ========================================
echo   完成！dist\KindleAutoCapture.exe
echo ========================================
explorer dist
pause
