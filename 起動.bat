@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: bin/ フォルダの ADB を優先して使う（インストール不要）
set "PATH=%~dp0bin;%PATH%"

:: セットアップ未完了チェック
if not exist "bin\adb.exe" (
    echo ADB が見つかりません。先に setup.bat を実行してください。
    pause & exit /b 1
)

python app_gui.py
