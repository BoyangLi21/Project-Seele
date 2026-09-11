@echo off
setlocal
cd /d "%~dp0.."
if not exist "run\saves\SEELE_TV_WORLD_PREVIEW_20260906\level.dat" (
    echo The local TV world preview save was not found.
    pause
    exit /b 1
)
if not exist "%JAVA_HOME%\bin\java.exe" set "JAVA_HOME=C:\Users\liboy\jdks\jdk-17.0.19+10"
set "PYTHONUTF8=1"
python tools\launch_rendered_client_r17.py
