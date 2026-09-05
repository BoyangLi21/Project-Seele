@echo off
setlocal
cd /d "%~dp0.."
if not exist "run\saves\SEELE_PYRAMID_TV_PREVIEW_20260905\level.dat" (
    echo The local pyramid preview save was not found.
    pause
    exit /b 1
)
if not exist "%JAVA_HOME%\bin\java.exe" set "JAVA_HOME=C:\Users\liboy\jdks\jdk-17.0.19+10"
call gradlew.bat --offline runClient -PstrictHighDetail=true -PquickPlayWorld=SEELE_PYRAMID_TV_PREVIEW_20260905
