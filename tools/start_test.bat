@echo off
setlocal
title Project SEELE - local test client
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
set "PYTHONUTF8=1"
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
)
rem Tigerar1's CC BY-SA mesh is the preferred local Unit-01 visual source.
rem Run it last so it replaces only Unit-01 while preserving other SmOd assets.
if exist "external-assets\incoming\evangelion-unit-01.zip" (
    python tools\make_tiger_unit01_pack.py
    if errorlevel 1 (
        echo Tigerar1 Unit-01 model generation failed.
        pause
        exit /b 1
    )
)
rem Install each remaining Tigerar1 EVA mesh as an incremental override.
rem Each source is independent: a missing download must not suppress the
rem variants that are already available locally.
if exist "external-assets\incoming\evangelion-unit-00.zip" (
    python tools\make_tiger_eva_variants_pack.py --only unit00
    if errorlevel 1 (
        echo Tigerar1 Unit-00 model generation failed.
        pause
        exit /b 1
    )
)
if exist "external-assets\incoming\evangelion-unit-02.zip" (
    python tools\make_tiger_eva_variants_pack.py --only unit02
    if errorlevel 1 (
        echo Tigerar1 Unit-02 model generation failed.
        pause
        exit /b 1
    )
)
if exist "external-assets\incoming\mass-production-evangelion.zip" (
    python tools\make_tiger_eva_variants_pack.py --only mass
    if errorlevel 1 (
        echo Tigerar1 Mass Production EVA model generation failed.
        pause
        exit /b 1
    )
)
rem Graft EUD's detailed Longinus model after the Tiger body converters;
rem otherwise the later Tiger geometry would restore the placeholder spear.
if exist "eud-1.1.0-forge-1.20.1.jar" (
    python tools\make_eud_weapon_pack.py
    if errorlevel 1 (
        echo EUD Longinus model generation failed.
        pause
        exit /b 1
    )
)
rem The real rifle is the final override. It needs both the ignored source
rem archive and the OBJ exported once by Blender.
if exist "external-assets\work\positron_rifle_export\positron_rifle.obj" (
    if exist "external-assets\incoming\positron-rifle-neon-genesis-evangelion.zip" (
        python tools\make_kantrophe_positron_pack.py --output run\resourcepacks\eva_real_model\assets\projectseele
        if errorlevel 1 (
            echo Kantrophe positron cannon generation failed.
            pause
            exit /b 1
        )
    )
)
python tools\validate_local_eva_pack.py
if errorlevel 1 (
    echo Local EVA resource-pack validation failed.
    pause
    exit /b 1
)
python tools\validate_impact_silo_contract.py
if errorlevel 1 (
    echo Third Impact or launch-silo structural validation failed.
    pause
    exit /b 1
)
python tools\render_tree_of_life_preview.py --layout current --strict
if errorlevel 1 (
    echo Tree-of-Life composition validation failed.
    pause
    exit /b 1
)
if /i "%~1"=="offline" (
    echo Rendering the complete offline EVA evidence matrix...
    python tools\render_eva_validation_matrix.py
    if errorlevel 1 (
        echo Offline EVA visual-contract validation failed.
        pause
        exit /b 1
    )
    echo Offline evidence matrix complete. Forge was not started.
    pause
    exit /b 0
)
echo.
echo Launch-silo test flow:
echo   1. Enter a creative world.
echo   2. Run /seele silo setup once on an open surface.
echo   3. Run /seele silo board from the high gantry.
echo   4. Wait for insertion, synchronization and automatic surface launch.
echo   /seele silo status reports the current interlock phase.
echo.
echo Starting Project SEELE test client (first launch takes a minute)...
if /i "%~1"=="visual" (
    echo Automated Visual Lab mode enabled.
    if /i "%~2"=="impact" (
        echo Capturing the complete Third Impact front tableau.
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=impact
    ) else if /i "%~2"=="unit00" (
        echo Capturing the complete Unit-00 pose suite.
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=unit00
    ) else if /i "%~2"=="unit02" (
        echo Capturing the complete Unit-02 pose suite.
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=unit02
    ) else if /i "%~2"=="mass" (
        echo Capturing Mass Production EVA idle, move, attack, revive, and ritual.
        echo Each state is recorded from seven fixed external views.
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=mass
    ) else if "%~2"=="" (
        echo Capturing the complete Unit-01 pose suite.
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=unit01
    ) else if /i "%~2"=="unit01" (
        echo Capturing the complete Unit-01 pose suite.
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=unit01
    ) else (
        echo Unknown visual target "%~2".
        echo Use: visual unit01, visual unit00, visual unit02, visual mass, or visual impact.
        pause
        exit /b 2
    )
) else (
    rem Local desktop testing is fail-closed: never display the obsolete
    rem fallback body when the active ResourceManager sees a stale/mixed pack.
    call gradlew.bat runClient -PstrictHighDetail=true
)
pause
