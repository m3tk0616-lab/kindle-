@echo off
rem ============================================================
rem  Kindle Auto Capture - Setup Script (ASCII-safe)
rem ============================================================

rem --- Force UTF-8 output but keep this script ASCII-safe ---
chcp 65001 >nul 2>&1

rem --- Re-launch in a persistent cmd if double-clicked from Explorer ---
if not defined KAC_RELAUNCHED (
    set "KAC_RELAUNCHED=1"
    start "Kindle Auto Capture Setup" cmd /k call "%~f0"
    exit /b
)

cd /d "%~dp0"
set "LOG=%~dp0setup_log.txt"

rem --- Init log file ---
> "%LOG%" echo === Kindle Auto Capture setup log ===
>> "%LOG%" echo Date: %date% %time%
>> "%LOG%" echo Dir : %~dp0
>> "%LOG%" echo.

echo.
echo ============================================================
echo   Kindle Auto Capture - Initial Setup
echo   (Run this once. Takes 2-5 minutes.)
echo ============================================================
echo.

rem ===== 1. Python =====================================================
echo [1/4] Checking Python...
>> "%LOG%" echo [1/4] Checking Python
where python >nul 2>&1
if errorlevel 1 (
    echo       Python not found. Trying winget install...
    >> "%LOG%" echo Python not found, trying winget
    winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements >> "%LOG%" 2>&1
    if errorlevel 1 (
        echo.
        echo  ----------------------------------------------------------
        echo   winget is not available on this system.
        echo   Your browser will open the Python download page.
        echo   IMPORTANT: Check "Add Python to PATH" during install.
        echo   After installing Python, run setup.bat again.
        echo  ----------------------------------------------------------
        echo.
        >> "%LOG%" echo winget failed, opened browser
        start "" "https://www.python.org/downloads/"
        pause
        exit /b 1
    )
    rem --- Update PATH for current session after winget install ---
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python312;%PATH%"
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python313\Scripts;%LOCALAPPDATA%\Programs\Python\Python313;%PATH%"
    where python >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  Python was installed but is not in PATH for this session.
        echo  Please close this window and run setup.bat again.
        echo.
        >> "%LOG%" echo Python installed but PATH not refreshed
        pause
        exit /b 1
    )
    echo       Python installed.
    >> "%LOG%" echo Python installed
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do (
        echo       OK: %%v
        >> "%LOG%" echo OK: %%v
    )
)

rem ===== 2. ADB ========================================================
echo [2/4] Checking ADB...
>> "%LOG%" echo [2/4] Checking ADB
if exist "%~dp0bin\adb.exe" (
    echo       OK: bin\adb.exe already exists
    >> "%LOG%" echo ADB already present
    goto adb_done
)
echo       Downloading ADB (~10 MB)...
>> "%LOG%" echo Downloading ADB
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile '_pt.zip' -UseBasicParsing -ErrorAction Stop; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }" >> "%LOG%" 2>&1
if not exist "_pt.zip" (
    echo.
    echo  ----------------------------------------------------------
    echo   ADB download failed.
    echo   Please check your internet connection and try again.
    echo   Details: setup_log.txt
    echo  ----------------------------------------------------------
    echo.
    >> "%LOG%" echo ADB download failed
    pause
    exit /b 1
)
echo       Extracting...
>> "%LOG%" echo Extracting
powershell -NoProfile -Command "Expand-Archive -Path '_pt.zip' -DestinationPath '_pt' -Force" >> "%LOG%" 2>&1
if not exist "bin" mkdir bin
copy /Y "_pt\platform-tools\adb.exe"          "bin\" >> "%LOG%" 2>&1
copy /Y "_pt\platform-tools\AdbWinApi.dll"    "bin\" >> "%LOG%" 2>&1
copy /Y "_pt\platform-tools\AdbWinUsbApi.dll" "bin\" >> "%LOG%" 2>&1
rmdir /s /q "_pt" 2>nul
del /q "_pt.zip" 2>nul
if not exist "bin\adb.exe" (
    echo.
    echo  ----------------------------------------------------------
    echo   Failed to install ADB.
    echo   See setup_log.txt for details.
    echo  ----------------------------------------------------------
    >> "%LOG%" echo ADB copy failed
    pause
    exit /b 1
)
echo       ADB installed: bin\adb.exe
>> "%LOG%" echo ADB installed
:adb_done

rem ===== 3. Python libraries ===========================================
echo [3/4] Installing Python libraries...
>> "%LOG%" echo [3/4] pip install
python -m pip install --upgrade pip >> "%LOG%" 2>&1
python -m pip install Pillow imagehash img2pdf PyMuPDF anthropic >> "%LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo  ----------------------------------------------------------
    echo   Failed to install Python libraries.
    echo   See setup_log.txt for details.
    echo  ----------------------------------------------------------
    >> "%LOG%" echo pip install failed
    pause
    exit /b 1
)
echo       OK
>> "%LOG%" echo pip install OK

rem ===== 4. Desktop shortcut ===========================================
echo [4/4] Creating desktop shortcut...
>> "%LOG%" echo [4/4] Shortcut
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Kindle Auto Capture.lnk'); $sc.TargetPath = '%~dp0run.bat'; $sc.WorkingDirectory = '%~dp0'; $sc.Save()" >> "%LOG%" 2>&1
echo       OK
>> "%LOG%" echo Shortcut OK

echo.
echo ============================================================
echo   DONE! Setup completed successfully.
echo.
echo   From now on, double-click the desktop shortcut:
echo     "Kindle Auto Capture"
echo.
echo   Log file: %LOG%
echo ============================================================
echo.
pause
