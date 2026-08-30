@echo off
setlocal EnableExtensions
title Project SEELE - EVA action review
cd /d "%~dp0.."
echo Opening SEELE_EVA_MOTION_LAB for manual action review.
echo Longinus motion is temporarily excluded from this review.
echo.
call "tools\start_test.bat" motion
exit /b %errorlevel%
