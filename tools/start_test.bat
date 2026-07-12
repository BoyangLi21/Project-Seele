@echo off
setlocal
rem Project SEELE - one-click test client.
rem Uses the standalone JDK 17 if JAVA_HOME is not already set to one.
if not exist "%JAVA_HOME%\bin\java.exe" set "JAVA_HOME=C:\Users\liboy\jdks\jdk-17.0.19+10"
set "SEELE_HOME=%~dp0.."
if not exist "%SEELE_HOME%\gradlew.bat" set "SEELE_HOME=D:\eva"
if not exist "%SEELE_HOME%\gradlew.bat" (
    echo Project SEELE repository was not found.
    echo Expected D:\eva or a launcher copied from the tools folder.
    pause
    exit /b 1
)
cd /d "%SEELE_HOME%"
rem SmOd is the required private Unit-01/02 model source.
rem Never fall back to Chikita: both converters used to share one output and
rem an old desktop launcher could silently replace the active model pack.
if not exist "evaaddon1-0.zip" (
    echo SmOd source evaaddon1-0.zip was not found in %SEELE_HOME%.
    echo Project SEELE will not start with a fallback EVA model.
    pause
    exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found; the local SmOd model pack cannot be generated.
    pause
    exit /b 1
)
python tools\make_smod_model_pack.py "evaaddon1-0.zip"
if errorlevel 1 (
    echo SmOd model-pack generation failed.
    pause
    exit /b 1
)
python tools\make_smod_angel_pack.py "evaaddon1-0.zip"
if errorlevel 1 (
    echo SmOd Angel model-pack generation failed.
    pause
    exit /b 1
)
if exist "eud-1.1.0-forge-1.20.1.jar" (
    python tools\make_eud_eva00_pack.py
    if errorlevel 1 (
        echo EUD Unit-00 model generation failed.
        pause
        exit /b 1
    )
    python tools\make_eud_weapon_pack.py
    if errorlevel 1 (
        echo EUD Longinus model generation failed.
        pause
        exit /b 1
    )
)
echo Starting Project SEELE test client (first launch takes a minute)...
call gradlew.bat runClient
pause
