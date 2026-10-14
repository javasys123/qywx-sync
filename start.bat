@echo off
echo ========================================
echo WeChat Archive Sync System
echo ========================================
echo.
echo Please select mode:
echo   1. Scheduler Mode (Recommended)
echo   2. Single Sync
echo.

set /p choice="Enter your choice (1-2): "

if "%choice%"=="1" (
    echo.
    echo Starting scheduler mode...
    python scheduler.py
) else if "%choice%"=="2" (
    echo.
    echo Starting single sync...
    python sync_archive.py
) else (
    echo.
    echo Invalid choice. Defaulting to scheduler mode...
    python scheduler.py
)

pause
