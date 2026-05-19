@echo off
chcp 65001 > nul

echo ====================================
echo  TOKAIRIT 2日目 動画ダウンロード
echo ====================================
echo.

REM Pythonの確認
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Python がインストールされていません。
    echo https://www.python.org からインストールしてください。
    pause
    exit /b
)

REM yt-dlpのインストール
echo yt-dlp をインストール中...
pip install -q yt-dlp
if %errorlevel% neq 0 (
    echo [エラー] yt-dlp のインストールに失敗しました。
    pause
    exit /b
)

REM 保存先フォルダ作成
mkdir "C:\Users\USER\Desktop\TOKAI RIT\TOKAIRIT2日目" 2>nul

echo.
echo ダウンロードを開始します（全29本）...
echo.

yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]" -o "C:\Users\USER\Desktop\TOKAI RIT\TOKAIRIT2日目\%(title)s.%(ext)s" "https://youtu.be/tMiNts3eaxI" "https://youtu.be/sj7pHP8Ybs8" "https://youtu.be/lmgpZ3z0Krg" "https://youtu.be/vzOR3-MGLes" "https://youtu.be/9WsxXNLb92U" "https://youtu.be/ZwNw8DXZQYQ" "https://youtu.be/dPPa1NbLcyY" "https://youtu.be/64elf63maPY" "https://youtu.be/6c-QHhll3mY" "https://youtu.be/q0ebHGBe37k" "https://youtu.be/B9dqPXc0IOY" "https://youtu.be/A8Em8mRsQJ0" "https://youtu.be/6RQUAo6-B44" "https://youtu.be/1XpFGHvZb3o" "https://youtu.be/jTeCEgo7Tfo" "https://youtu.be/eE_jBdMslfE" "https://youtu.be/S_XDSLKjQQs" "https://youtu.be/pMzlJstN1p4" "https://youtu.be/18pW1mNdIyE" "https://youtu.be/usrjxepjIo4" "https://youtu.be/Is6eTg5wcCI" "https://youtu.be/MygcjFdlauU" "https://youtu.be/gsCusW_6_hg" "https://youtu.be/PdxDOSQSyQM" "https://youtu.be/rGBxIfDEN-s" "https://youtu.be/t6Z9rqtDSec" "https://youtu.be/zDOwKm_XpPs" "https://youtu.be/De1YWre99iM" "https://youtu.be/LZKKQy-iWPY"

echo.
echo ====================================
echo  完了しました！
echo ====================================
pause
