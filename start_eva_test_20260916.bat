@echo off
setlocal
title Project SEELE - TV world acceptance 2026-09-16
pushd "%~dp0"
if errorlevel 1 exit /b 1

set "SEELE_CHECK_ONLY=0"
if /i "%~1"=="--check" set "SEELE_CHECK_ONLY=1"
if not "%~1"=="" if not "%SEELE_CHECK_ONLY%"=="1" goto usage
if not "%~2"=="" goto usage

set "SEELE_EXIT_CODE=1"
if not exist "tools\launch_rendered_client_r17.py" (
    echo ERROR: Keep this BAT in the Project SEELE repository root.
    goto failed
)
if not exist "run\saves\SEELE_TV_WORLD_PREVIEW_20260906\level.dat" (
    echo ERROR: The current TV world is missing.
    goto failed
)
if not exist "run\resourcepacks\eva_real_model\pack.mcmeta" (
    echo ERROR: The local EVA model resource pack is missing.
    goto failed
)

set "SEELE_PYTHON="
if exist "C:\Python314\python.exe" set "SEELE_PYTHON=C:\Python314\python.exe"
if not defined SEELE_PYTHON for %%P in (python.exe) do set "SEELE_PYTHON=%%~$PATH:P"
if not defined SEELE_PYTHON (
    echo ERROR: Python was not found. Install Python or add it to PATH.
    goto failed
)
set "PYTHONUTF8=1"
set "OPENBLAS_NUM_THREADS=1"

echo Project SEELE - current TV world, local manual acceptance
echo World: SEELE_TV_WORLD_PREVIEW_20260906
echo Client heap: 6 GB. Exact terrain: 24 chunks. LOD: disabled.
echo Guide: %CD%\docs\MANUAL_ACCEPTANCE_20260916.md
echo Close any other Minecraft instance using this world before starting.
echo.
if "%SEELE_CHECK_ONLY%"=="1" goto check

"%SEELE_PYTHON%" "tools\launch_rendered_client_r17.py" --world SEELE_TV_WORLD_PREVIEW_20260906 --heap 6G
set "SEELE_EXIT_CODE=%ERRORLEVEL%"
if not "%SEELE_EXIT_CODE%"=="0" goto failed
goto done

:check
"%SEELE_PYTHON%" "tools\launch_rendered_client_r17.py" --world SEELE_TV_WORLD_PREVIEW_20260906 --heap 6G --prepare-only
set "SEELE_EXIT_CODE=%ERRORLEVEL%"
if not "%SEELE_EXIT_CODE%"=="0" goto failed
echo Launch preparation passed. Minecraft was not started.
goto done

:usage
echo Usage: start_eva_test_20260916.bat [--check]
echo Double-click to play. --check prepares the launch without starting Minecraft.
set "SEELE_EXIT_CODE=2"
goto done

:failed
echo.
echo Launch failed. Keep the error above for diagnosis.
echo Game log, if Minecraft started: %CD%\run\logs\latest.log
if "%SEELE_CHECK_ONLY%"=="0" pause

:done
popd
exit /b %SEELE_EXIT_CODE%
