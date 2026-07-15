@echo off
setlocal

set "ROOT=%~dp0.."
set "SCRIPT=%ROOT%\tools\blender_pose_lab.py"
set "LAB=%ROOT%\external-assets\work\pose-lab\Project_SEELE_Unit01_PoseLab.blend"

if defined BLENDER_EXE (
    set "BLENDER=%BLENDER_EXE%"
) else (
    set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
)

if not exist "%BLENDER%" (
    echo Blender was not found at:
    echo   %BLENDER%
    echo Set BLENDER_EXE to the full blender.exe path and run this file again.
    pause
    exit /b 1
)

if not exist "%LAB%" (
    echo Pose Lab does not exist yet. Building it now...
    call "%ROOT%\tools\rebuild_pose_lab.bat"
    if errorlevel 1 exit /b 1
)

start "Project SEELE Pose Lab" "%BLENDER%" "%LAB%" --python "%SCRIPT%" -- --interactive
exit /b 0
