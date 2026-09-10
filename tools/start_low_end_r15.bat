@echo off
setlocal
title Project SEELE - low-end client
set "PYTHONUTF8=1"
python "%~dp0launch_low_end_r15.py"
if errorlevel 1 pause
