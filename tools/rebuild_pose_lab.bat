@echo off
setlocal

set "ROOT=%~dp0.."
set "SCRIPT=%ROOT%\tools\blender_pose_lab.py"
set "LABROOT=%ROOT%\external-assets\work\pose-lab"
set "CHECK=%LABROOT%\build_check.png"

if defined BLENDER_EXE (
    set "BLENDER=%BLENDER_EXE%"
) else (
    set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)

if not exist "%BLENDER%" (
    echo Blender was not found at:
    echo   %BLENDER%
    pause
    exit /b 1
)

echo Rebuilding Project SEELE Unit-01 Pose Lab...
echo Existing saved manual pose edits in the fixed .blend file will be replaced.
"%BLENDER%" --background --python "%SCRIPT%" -- --build --validate --render-check "%CHECK%"
if errorlevel 1 (
    echo Pose Lab build failed. Read the Blender errors above.
    pause
    exit /b 1
)

echo Pose Lab build and validation passed.
echo Check render: %CHECK%
exit /b 0
