@echo off
title Kindle Auto Capture

:: Move to script directory
cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python が見つかりません。Python 3.10 以上をインストールしてください。
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist ".deps_installed" (
    echo 依存ライブラリをインストールしています...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] インストールに失敗しました。
        pause
        exit /b 1
    )
    echo. > .deps_installed
)

:: Open browser after short delay
start "" timeout /t 2 /nobreak >nul & start http://localhost:8000

:: Start server
echo.
echo ========================================
echo   Kindle Auto Capture 起動中...
echo   ブラウザで http://localhost:8000 を開いてください
echo   終了するには Ctrl+C を押してください
echo ========================================
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
