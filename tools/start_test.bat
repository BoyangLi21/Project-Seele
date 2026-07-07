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
rem Refresh the private local-only model pack when its source jar is present.
if exist "Rei_Chikita_Mod_1.1.7b__jv1.20.1.jar" (
    where python >nul 2>nul
    if not errorlevel 1 python tools\make_model_pack.py "Rei_Chikita_Mod_1.1.7b__jv1.20.1.jar"
)
echo Starting Project SEELE test client (first launch takes a minute)...
call gradlew.bat runClient
pause
