@echo off
chcp 65001 >nul
title Kindle Auto Capture — セットアップ
cd /d "%~dp0"

echo.
echo ════════════════════════════════════════════
echo   Kindle Auto Capture  初回セットアップ
echo   ※ 初回だけ実行してください（2〜5分）
echo ════════════════════════════════════════════
echo.

:: ─── 1. Python チェック ──────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [1/4] Python が見つかりません。自動インストールします...
    winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  winget が使えません。ブラウザでインストールページを開きます。
        echo  ※「Add Python to PATH」に必ずチェックを入れてください。
        start https://www.python.org/downloads/
        echo  インストール後、もう一度 setup.bat を実行してください。
        pause & exit /b 1
    )
    :: 新しい PATH を反映
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    echo  Python: インストール完了
) else (
    echo [1/4] Python: OK
)

:: ─── 2. ADB 自動ダウンロード ────────────────────────────────────
if exist "bin\adb.exe" (
    echo [2/4] ADB: OK （既にあります）
    goto adb_done
)
echo [2/4] ADB をダウンロード中... （約 10MB）
powershell -Command ^
  "Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile '_pt.zip' -UseBasicParsing"
if not exist "_pt.zip" (
    echo  ダウンロード失敗。ネットワーク接続を確認してください。
    pause & exit /b 1
)
powershell -Command "Expand-Archive -Path '_pt.zip' -DestinationPath '_pt' -Force"
if not exist "bin" mkdir bin
copy "_pt\platform-tools\adb.exe"          "bin\" >nul
copy "_pt\platform-tools\AdbWinApi.dll"    "bin\" >nul 2>&1
copy "_pt\platform-tools\AdbWinUsbApi.dll" "bin\" >nul 2>&1
rmdir /s /q "_pt"
del "_pt.zip"
echo  ADB: ダウンロード完了
:adb_done

:: ─── 3. Python ライブラリ ───────────────────────────────────────
echo [3/4] ライブラリをインストール中...
python -m pip install --upgrade pip -q
python -m pip install Pillow imagehash img2pdf PyMuPDF anthropic -q
if errorlevel 1 (
    echo  ライブラリのインストールに失敗しました。
    pause & exit /b 1
)
echo  ライブラリ: OK

:: ─── 4. デスクトップにショートカット作成 ─────────────────────────
echo [4/4] デスクトップにショートカットを作成中...
powershell -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Kindle Auto Capture.lnk');" ^
  "$sc.TargetPath = '%~dp0起動.bat';" ^
  "$sc.WorkingDirectory = '%~dp0';" ^
  "$sc.Save()"
echo  ショートカット: OK

echo.
echo ════════════════════════════════════════════
echo   ✅ セットアップ完了！
echo.
echo   次回からはデスクトップの
echo   「Kindle Auto Capture」をダブルクリックするだけです。
echo ════════════════════════════════════════════
echo.
pause
