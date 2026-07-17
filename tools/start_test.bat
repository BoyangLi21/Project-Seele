@echo off
setlocal EnableExtensions EnableDelayedExpansion
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
rem SmOd remains the required private base/Angel source.  Its old Unit-01/02
rem conversions are overwritten below; the active four EVA bodies are the
rem locally downloaded Tigerar1 meshes.  Never fall back to Chikita: an old
rem desktop launcher could silently replace the reviewed resource pack.
if not exist "evaaddon1-0.zip" (
    echo SmOd base/Angel source evaaddon1-0.zip was not found in %SEELE_HOME%.
    echo Project SEELE will not start with an incomplete local resource pack.
    pause
    exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found; the local EVA resource pack cannot be generated.
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
rem Tigerar1's CC BY-SA meshes are the active local EVA body sources.  Install
rem them after SmOd so no legacy body can survive a weapon/stance transition.
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
rem Adapt the downloaded common knife, EVA-02 weapons and entry plug only
rem after all Tiger bodies exist, because every attachment reads their final
rem reviewed hand/back socket pivots. This local pack is never redistributed.
if exist "external-assets\incoming\progressive-knife.zip" if exist "external-assets\incoming\eva-02-rebuild-version-not-rigged.zip" if exist "eud-1.1.0-forge-1.20.1.jar" (
    python tools\make_downloaded_eva_accessories_pack.py
    if errorlevel 1 (
        echo Downloaded EVA accessory generation failed.
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
rem Prefer the exact locally reviewed TV Pallet Rifle when its ignored source
rem is installed. The procedural MIT model remains a safe fallback.
set "SEELE_TV_RIFLE=0"
if exist "external-assets\work\pallet-rifle-oni\palett\palett.obj" if exist "external-assets\work\pallet-rifle-oni\palett\palett.bmp" set "SEELE_TV_RIFLE=1"
if "%SEELE_TV_RIFLE%"=="1" (
    python tools\make_downloaded_pallet_rifle_pack.py
    if errorlevel 1 (
        echo Local TV Pallet Rifle generation failed.
        pause
        exit /b 1
    )
) else (
    python tools\make_original_eva_rifle.py
    if errorlevel 1 (
        echo Original EVA pallet SMG generation failed.
        pause
        exit /b 1
    )
)
set "SEELE_TV_RIFLE="
rem Original hand-carried N2 self-destruction device. It reads the final Tiger
rem hand socket and is never substituted by the old SmOd placeholder cube.
python tools\make_original_n2_device.py
if errorlevel 1 (
    echo Original EVA-carried N2 device generation failed.
    pause
    exit /b 1
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
python tools\validate_tokyo3_retraction.py
if errorlevel 1 (
    echo Tokyo-3 retractable-building validation failed.
    pause
    exit /b 1
)
python tools\validate_geofront_contract.py
if errorlevel 1 (
    echo GeoFront dimension and map validation failed.
    pause
    exit /b 1
)
python tools\validate_weapon_systems.py
if errorlevel 1 (
    echo EVA firearm, scope or strategic-explosion validation failed.
    pause
    exit /b 1
)
if /i "%~1"=="offline" (
    set "OFFLINE_FAILED=0"
    echo Running the fail-closed offline visual recovery suite...
    python tools\validate_third_person_pose.py
    if errorlevel 1 set "OFFLINE_FAILED=1"
    python tools\validate_crawl_pose.py
    if errorlevel 1 set "OFFLINE_FAILED=1"
    python tools\validate_low_stance_pose.py
    if errorlevel 1 set "OFFLINE_FAILED=1"
    python tools\validate_crucified_pose.py
    if errorlevel 1 set "OFFLINE_FAILED=1"
    python tools\render_launch_silo_preview.py --strict
    if errorlevel 1 set "OFFLINE_FAILED=1"
    python tools\render_tokyo3_preview.py --strict
    if errorlevel 1 set "OFFLINE_FAILED=1"
    python tools\render_tree_of_life_preview.py --layout current --strict
    if errorlevel 1 set "OFFLINE_FAILED=1"
    python tools\render_eva_validation_matrix.py
    if errorlevel 1 set "OFFLINE_FAILED=1"
    if "!OFFLINE_FAILED!"=="1" (
        echo One or more offline visual-recovery gates failed.
        echo Inspect the generated reports and PNG evidence before running Forge.
        pause
        exit /b 1
    )
    echo Offline visual-recovery suite complete. Forge was not started.
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
echo   /seele tokyo3 setup builds the connected surface battle district.
echo   /seele tokyo3 overview returns to the skyline observation deck.
echo.
echo Starting Project SEELE test client (first launch takes a minute)...
if /i "%~1"=="visual" (
    echo Automated Visual Lab mode enabled.
    if /i "%~2"=="all" (
        echo Capturing Unit-01, Unit-00, Unit-02, Mass Production, Tokyo-3, retraction, GeoFront, linked sortie, silo and Third Impact.
        echo Each client closes automatically before the next target starts.
        for %%U in (unit01 unit00 unit02 mass tokyo3 tokyo3_retraction geofront geofront_sortie silo impact) do (
            echo.
            echo === Visual suite target: %%U ===
            python tools\validate_visual_capture_run.py begin %%U
            if errorlevel 1 exit /b 1
            call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=%%U
            if errorlevel 1 (
                echo Visual suite stopped because %%U failed.
                exit /b 1
            )
            python tools\validate_visual_capture_run.py verify %%U
            if errorlevel 1 (
                echo Visual suite stopped because %%U produced invalid evidence.
                exit /b 1
            )
        )
        echo Complete Visual Lab suite finished.
    ) else if /i "%~2"=="tokyo3" (
        echo Building and capturing the complete Tokyo-3 surface sortie district.
        echo Four audited views cover the skyline, sortie road, power grid and Angel plaza.
        python tools\validate_visual_capture_run.py begin tokyo3
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=tokyo3
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify tokyo3
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="tokyo3_retraction" (
        echo Capturing Tokyo-3 armour towers deployed, half-lowered, retracted and restored.
        echo The full persisted cycle takes roughly 100 seconds and closes automatically.
        python tools\validate_visual_capture_run.py begin tokyo3_retraction
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=tokyo3_retraction
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify tokyo3_retraction
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="geofront" (
        echo Building and capturing the independent GeoFront development cavern.
        echo Four audited views cover the cavern, NERV pyramid, LCL lake and lift terminals.
        python tools\validate_visual_capture_run.py begin geofront
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=geofront
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify geofront
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="geofront_sortie" (
        echo Capturing the real linked launch from GeoFront into the Tokyo-3 surface district.
        echo Four state-gated frames cover three-unit readiness, plug lock, ascent and arrival.
        python tools\validate_visual_capture_run.py begin geofront_sortie
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=geofront_sortie
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify geofront_sortie
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="silo" (
        echo Capturing the real entry-plug synchronization and launch-catapult sequence.
        echo Six frames are state-gated: gantry, plug travel, cockpit, hatch, ascent, surface.
        python tools\validate_visual_capture_run.py begin silo
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=silo
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify silo
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="impact" (
        echo Capturing the complete Third Impact front tableau.
        python tools\validate_visual_capture_run.py begin impact
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=impact
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify impact
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="unit00" (
        echo Capturing the complete Unit-00 pose suite.
        python tools\validate_visual_capture_run.py begin unit00
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=unit00
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify unit00
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="unit02" (
        echo Capturing the complete Unit-02 pose suite.
        python tools\validate_visual_capture_run.py begin unit02
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=unit02
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify unit02
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="mass" (
        echo Capturing Mass Production EVA idle, move, attack, revive, and ritual.
        echo Each state is recorded from seven fixed external views.
        python tools\validate_visual_capture_run.py begin mass
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=mass
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify mass
        if errorlevel 1 exit /b 1
    ) else if "%~2"=="" (
        echo Capturing the complete Unit-01 pose suite.
        python tools\validate_visual_capture_run.py begin unit01
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=unit01
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify unit01
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="unit01" (
        echo Capturing the complete Unit-01 pose suite.
        python tools\validate_visual_capture_run.py begin unit01
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=SEELE_VISUAL_TEST_2 -PvisualCapture=true -PvisualCaptureUnit=unit01
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify unit01
        if errorlevel 1 exit /b 1
    ) else (
        echo Unknown visual target "%~2".
        echo Use: visual all, unit01, unit00, unit02, mass, tokyo3, tokyo3_retraction, geofront, geofront_sortie, silo, or impact.
        pause
        exit /b 2
    )
) else (
    rem Local desktop testing is fail-closed: never display the obsolete
    rem fallback body when the active ResourceManager sees a stale/mixed pack.
    call gradlew.bat runClient -PstrictHighDetail=true
)
pause
