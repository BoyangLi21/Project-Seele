@echo off
setlocal
title Project SEELE - R30 facilities, pilot missions and UN operations
pushd "%~dp0"
if errorlevel 1 exit /b 1
set "SEELE_CHECK="
set "SEELE_SHADERS="
set "SEELE_EXIT_CODE=1"
:args
if "%~1"=="" goto ready
if /i "%~1"=="--check" (
    set "SEELE_CHECK=--prepare-only"
) else if /i "%~1"=="--no-shaders" (
    set "SEELE_SHADERS="
) else if /i "%~1"=="--city-shaders" (
    set "SEELE_SHADERS=--city-shaders"
) else goto usage
shift
goto args
:ready
if not exist "run\saves\SEELE_R30_WORLD\r30_ready.json" (
    echo ERROR: The R30 world installation is not ready.
    goto failed
)
if not exist "run\resourcepacks\eva_real_model\pack.mcmeta" (
    echo ERROR: The private EVA model pack is missing.
    goto failed
)
set "SEELE_PYTHON="
if exist "C:\Python314\python.exe" set "SEELE_PYTHON=C:\Python314\python.exe"
if not defined SEELE_PYTHON for %%P in (python.exe) do set "SEELE_PYTHON=%%~$PATH:P"
if not defined SEELE_PYTHON (
    echo ERROR: Python is required.
    goto failed
)
set "PYTHONUTF8=1"
set "OPENBLAS_NUM_THREADS=1"
echo R30 - protocol 34. Use the matching R30 client and server.
echo Guide: %CD%\docs\MANUAL_ACCEPTANCE_R30.md
echo World: SEELE_R30_WORLD
"%SEELE_PYTHON%" tools\launch_rendered_client_r17.py --world SEELE_R30_WORLD --heap 6G %SEELE_SHADERS% %SEELE_CHECK%
set "SEELE_EXIT_CODE=%ERRORLEVEL%"
if not "%SEELE_EXIT_CODE%"=="0" goto failed
goto done
:usage
echo Usage: start_eva_test_r30.bat [--check] [--city-shaders] [--no-shaders]
set "SEELE_EXIT_CODE=2"
goto done
:failed
echo.
echo Check the error above and run\logs\latest.log.
if "%SEELE_CHECK%"=="" pause
:done
popd
exit /b %SEELE_EXIT_CODE%
