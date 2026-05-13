@echo off
chcp 65001 >nul 2>&1

:: ウィンドウを必ず開いたまま保持する仕組み
:: 最初の引数なしで起動したとき → cmd /k で自分自身を再起動（ウィンドウが消えなくなる）
if "%~1"=="" (
    start "Kindle Auto Capture セットアップ" cmd /k "%~f0" STARTED
    exit
)

cd /d "%~dp0"
set "LOG=%~dp0setup_log.txt"

echo ════════════════════════════════════════════  > "%LOG%"
echo    Kindle Auto Capture  セットアップログ      >> "%LOG%"
echo    %date% %time%                              >> "%LOG%"
echo ════════════════════════════════════════════  >> "%LOG%"
echo.                                              >> "%LOG%"

echo.
echo ════════════════════════════════════════════
echo   Kindle Auto Capture  初回セットアップ
echo   ※ 初回だけ実行してください（2〜5分）
echo ════════════════════════════════════════════
echo.

:: ─── 1. Python チェック ──────────────────────────────────────────
echo [1/4] Python を確認中...
echo [1/4] Python チェック開始 >> "%LOG%"
python --version >> "%LOG%" 2>&1
if errorlevel 1 (
    echo       Python が見つかりません。自動インストールを試みます...
    echo       Python が見つかりません。winget でインストール試行 >> "%LOG%"
    winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements >> "%LOG%" 2>&1
    if errorlevel 1 (
        echo.
        echo  ╔══════════════════════════════════════════════╗
        echo  ║  winget が使えない環境です。                  ║
        echo  ║  ブラウザが開きますので手動でインストール      ║
        echo  ║  してください。                               ║
        echo  ║                                              ║
        echo  ║  ※ インストール時に                           ║
        echo  ║    「Add Python to PATH」に                   ║
        echo  ║     チェックを入れてください！                 ║
        echo  ╚══════════════════════════════════════════════╝
        echo.
        echo  winget 失敗 → ブラウザを開いて終了 >> "%LOG%"
        start https://www.python.org/downloads/
        echo  インストール後、もう一度 setup.bat を実行してください。
        echo.
        pause
        exit /b 1
    )
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    echo       Python: インストール完了
    echo       Python インストール完了 >> "%LOG%"
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do (
        echo       %%v — OK
        echo       %%v — OK >> "%LOG%"
    )
)

:: ─── 2. ADB 自動ダウンロード ────────────────────────────────────
echo [2/4] ADB を確認中...
echo [2/4] ADB チェック開始 >> "%LOG%"
if exist "bin\adb.exe" (
    echo       ADB: OK （既にあります）
    echo       ADB: 既存 OK >> "%LOG%"
    goto adb_done
)
echo       ADB をダウンロード中... （約 10MB）
echo       ADB ダウンロード開始 >> "%LOG%"
powershell -Command "Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile '_pt.zip' -UseBasicParsing" >> "%LOG%" 2>&1
if not exist "_pt.zip" (
    echo.
    echo  ╔══════════════════════════════════════════════╗
    echo  ║  ADB のダウンロードに失敗しました。           ║
    echo  ║  インターネット接続を確認してください。        ║
    echo  ╚══════════════════════════════════════════════╝
    echo.
    echo  _pt.zip ダウンロード失敗 >> "%LOG%"
    pause
    exit /b 1
)
echo       解凍中...
powershell -Command "Expand-Archive -Path '_pt.zip' -DestinationPath '_pt' -Force" >> "%LOG%" 2>&1
if not exist "bin" mkdir bin
copy "_pt\platform-tools\adb.exe"          "bin\" >> "%LOG%" 2>&1
copy "_pt\platform-tools\AdbWinApi.dll"    "bin\" >> "%LOG%" 2>&1
copy "_pt\platform-tools\AdbWinUsbApi.dll" "bin\" >> "%LOG%" 2>&1
rmdir /s /q "_pt" >> "%LOG%" 2>&1
del "_pt.zip" >> "%LOG%" 2>&1
echo       ADB: ダウンロード完了
echo       ADB: ダウンロード完了 >> "%LOG%"
:adb_done

:: ─── 3. Python ライブラリ ───────────────────────────────────────
echo [3/4] ライブラリをインストール中...
echo [3/4] pip インストール開始 >> "%LOG%"
python -m pip install --upgrade pip >> "%LOG%" 2>&1
python -m pip install Pillow imagehash img2pdf PyMuPDF anthropic >> "%LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo  ╔══════════════════════════════════════════════╗
    echo  ║  ライブラリのインストールに失敗しました。     ║
    echo  ║  setup_log.txt を確認してください。           ║
    echo  ╚══════════════════════════════════════════════╝
    echo.
    echo  pip インストール失敗 >> "%LOG%"
    pause
    exit /b 1
)
echo       ライブラリ: OK
echo       pip インストール完了 >> "%LOG%"

:: ─── 4. デスクトップにショートカット作成 ─────────────────────────
echo [4/4] デスクトップにショートカットを作成中...
echo [4/4] ショートカット作成 >> "%LOG%"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Kindle Auto Capture.lnk'); $sc.TargetPath = '%~dp0起動.bat'; $sc.WorkingDirectory = '%~dp0'; $sc.Save()" >> "%LOG%" 2>&1
echo       ショートカット: OK
echo       ショートカット作成完了 >> "%LOG%"

echo.
echo ════════════════════════════════════════════
echo   ✅ セットアップ完了！
echo.
echo   次回からはデスクトップの
echo   「Kindle Auto Capture」をダブルクリック。
echo.
echo   ログ: %LOG%
echo ════════════════════════════════════════════
echo.
echo   このウィンドウは閉じてください。
echo   セットアップ完了 >> "%LOG%"
