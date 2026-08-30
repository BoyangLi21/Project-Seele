@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "tools\start_motion_lab.bat" (
    echo Project SEELE motion-lab launcher was not found.
    pause
    exit /b 1
)
call "tools\start_motion_lab.bat"
exit /b %errorlevel%
