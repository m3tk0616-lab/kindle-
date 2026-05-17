@echo off
rem ============================================================
rem  Kindle Auto Capture - Launcher
rem ============================================================
chcp 65001 >nul 2>&1
cd /d "%~dp0"

rem --- Put bundled adb on PATH ---
set "PATH=%~dp0bin;%PATH%"

rem --- Sanity check ---
if not exist "bin\adb.exe" (
    echo.
    echo  ----------------------------------------------------------
    echo   ADB not found.  Please run setup.bat first.
    echo  ----------------------------------------------------------
    echo.
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ----------------------------------------------------------
    echo   Python not found.  Please run setup.bat first.
    echo  ----------------------------------------------------------
    echo.
    pause
    exit /b 1
)

rem --- Launch the GUI ---
python app_gui.py
if errorlevel 1 (
    echo.
    echo  ----------------------------------------------------------
    echo   The app exited with an error.  See messages above.
    echo  ----------------------------------------------------------
    echo.
    pause
)
