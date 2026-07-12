@echo off
rem Stable desktop shim: always execute the current repository launcher.
rem Keeping logic in one tracked file prevents an old desktop copy from
rem rebuilding stale models or restoring the wrong resource-pack order.
if not exist "D:\eva\tools\start_test.bat" (
    echo Project SEELE launcher was not found at D:\eva\tools\start_test.bat.
    pause
    exit /b 1
)
call "D:\eva\tools\start_test.bat" %*
