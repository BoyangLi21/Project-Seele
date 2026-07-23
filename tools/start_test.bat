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
rem Local-only Ars Nouveau integration: Skyweave renders the real skybox on
rem the buried GeoFront sphere. ForgeGradle must remap these production jars
rem before a dev launch, so never load their raw copies from run\mods.
if exist "run\mods\ars_nouveau-1.20.1-4.12.7-all.jar" del /Q "run\mods\ars_nouveau-1.20.1-4.12.7-all.jar"
if exist "run\mods\curios-forge-5.14.1+1.20.1.jar" del /Q "run\mods\curios-forge-5.14.1+1.20.1.jar"
if not exist ".Codex\local-mods" mkdir ".Codex\local-mods"
set "SEELE_MC_MODS=C:\Users\liboy\AppData\Roaming\.minecraft\mods"
if exist "%SEELE_MC_MODS%\ars_nouveau-1.20.1-4.12.7-all.jar" copy /Y "%SEELE_MC_MODS%\ars_nouveau-1.20.1-4.12.7-all.jar" ".Codex\local-mods\ars-nouveau-4.12.7.jar" >nul
if exist "%SEELE_MC_MODS%\curios-forge-5.14.1+1.20.1.jar" copy /Y "%SEELE_MC_MODS%\curios-forge-5.14.1+1.20.1.jar" ".Codex\local-mods\curios-forge-1.20.1-5.14.1.jar" >nul
set "SEELE_MC_MODS="
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
rem Prepare the user's private map downloads with the Python 3.12 runtime that
rem carries nbtlib. Converted structures and the staged save stay under run/
rem and are never packaged into the mod jar.
set "SEELE_MAP_PY=C:\Users\liboy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%SEELE_MAP_PY%" set "SEELE_MAP_PY=python"
if exist "external-assets\work\maps\source_eva_bilibili\EVA\level.dat" if exist "external-assets\work\maps\source_nerv_command\Nerv Comand Module\level.dat" if exist "external-assets\incoming\maps\tokyo-3-type-skyscrapper1-converted.schem" (
    set "SEELE_OLD_PYTHONPATH=!PYTHONPATH!"
    if exist ".Codex\pydeps312" set "PYTHONPATH=%SEELE_HOME%\.Codex\pydeps312"
    "%SEELE_MAP_PY%" tools\prepare_local_map_assets.py
    set "SEELE_MAP_RESULT=!ERRORLEVEL!"
    set "PYTHONPATH=!SEELE_OLD_PYTHONPATH!"
    set "SEELE_OLD_PYTHONPATH="
    if not "!SEELE_MAP_RESULT!"=="0" (
        echo Private Tokyo-3/NERV map preparation failed.
        pause
        exit /b 1
    )
    set "SEELE_MAP_RESULT="
)
set "SEELE_MAP_PY="
set "SEELE_VISUAL_WORLD=SEELE_VISUAL_TEST_2"
if exist "run\saves\SEELE_TOKYO3_COMPLETE\level.dat" set "SEELE_VISUAL_WORLD=SEELE_TOKYO3_COMPLETE"
if exist "run\saves\SEELE_TOKYO3_REBUILT\level.dat" set "SEELE_VISUAL_WORLD=SEELE_TOKYO3_REBUILT"
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
python tools\make_lilith_model_pack.py
if errorlevel 1 (
    echo Kiki Lilith local model generation failed.
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
python tools\validate_eva_logistics_contract.py
if errorlevel 1 (
    echo EVA wet-hangar, transfer or recovery validation failed.
    pause
    exit /b 1
)
python tools\validate_dummy_pilot_contract.py
if errorlevel 1 (
    echo Dummy pilot, external entry-plug or command-feed validation failed.
    pause
    exit /b 1
)
python tools\validate_weapon_systems.py
if errorlevel 1 (
    echo EVA firearm, scope or strategic-explosion validation failed.
    pause
    exit /b 1
)
python tools\validate_angel_siege_contract.py
if errorlevel 1 (
    echo Persistent Angel siege validation failed.
    pause
    exit /b 1
)
python tools\validate_lcl_contract.py
if errorlevel 1 (
    echo LCL gameplay validation failed.
    pause
    exit /b 1
)
python tools\validate_eva_power_contract.py
if errorlevel 1 (
    echo EVA internal and umbilical power validation failed.
    pause
    exit /b 1
)
python tools\validate_eva_sync_contract.py
if errorlevel 1 (
    echo Persistent EVA pilot synchronization validation failed.
    pause
    exit /b 1
)
python tools\validate_eva_berserk_contract.py
if errorlevel 1 (
    echo EVA Unit-01 berserk validation failed.
    pause
    exit /b 1
)
python tools\validate_eva_armament_contract.py
if errorlevel 1 (
    echo Persistent EVA armament-rack validation failed.
    pause
    exit /b 1
)
python tools\validate_multiplayer_operations_contract.py
if errorlevel 1 (
    echo NERV multiplayer crew and dedicated-server validation failed.
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
echo Continuous Tokyo-3 / GeoFront test flow:
echo   1. The fresh normal-terrain SEELE_TOKYO3_REBUILT world opens automatically when available.
echo   2. Run /seele geofront setup once only if the integrated map has not been initialized.
echo   3. Run /seele geofront hangar to enter the shoulder-level wet-cage gallery.
echo   4. Run /seele eva status all. A human or /seele eva dummy start unit01 must board the suspended white plug first.
echo   5. MAGI CHECK retracts the split bridge, inserts the physical plug, drains LCL and moves the locked EVA to its silo.
echo   6. EVA-01 RELEASE is still required at the main command console; its 16:9 panel can show TRAINING LIVE from the Dummy.
echo   7. To recover, park motionless on the matching surface deck; a second operator presses its supported button in /seele geofront recovery_control.
echo   8. /seele eva reset unit00^|unit01^|unit02^|all restores the canonical airframe, bridge, LCL and external plug.
echo   /seele geofront surface is a developer camera shortcut only.
echo   /seele geofront exit returns to the original world.
echo   /seele geofront audit and sortie_audit report both map and EVA links.
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
            call gradlew.bat runClient -PquickPlayWorld=!SEELE_VISUAL_WORLD! -PvisualCapture=true -PvisualCaptureUnit=%%U
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
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=tokyo3
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify tokyo3
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="tokyo3_retraction" (
        echo Capturing Tokyo-3 armour towers deployed, half-lowered, retracted and restored.
        echo The full 312-layer down-and-up cycle takes roughly 11 minutes and closes automatically.
        python tools\validate_visual_capture_run.py begin tokyo3_retraction
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=tokyo3_retraction
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify tokyo3_retraction
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="geofront" (
        echo Building and capturing the sealed GeoFront below the connected Tokyo-3 world.
        echo Thirteen audited views cover the cavern, command room, sealed support rooms, Central/Terminal Dogma, LCL and lift terminals.
        python tools\validate_visual_capture_run.py begin geofront
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=geofront
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify geofront
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="tokyo3_battle" (
        echo Capturing Operation Yashima over the integrated Tokyo-3 map.
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=tokyo3_battle
        exit /b %errorlevel%
    ) else if /i "%~2"=="geofront_sortie" (
        echo Capturing one EVA entity through the real GeoFront-to-Tokyo-3 shaft.
        echo Five state-gated frames prove readiness, plug lock, live pilot telemetry, mid-shaft height and same-dimension arrival.
        python tools\validate_visual_capture_run.py begin geofront_sortie
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=geofront_sortie
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify geofront_sortie
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="silo" (
        echo Capturing the real entry-plug synchronization and launch-catapult sequence.
        echo Six frames are state-gated: gantry, plug travel, cockpit, hatch, ascent, surface.
        python tools\validate_visual_capture_run.py begin silo
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=silo
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify silo
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="impact" (
        echo Capturing the complete Third Impact front tableau.
        python tools\validate_visual_capture_run.py begin impact
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=impact
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify impact
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="unit00" (
        echo Capturing the complete Unit-00 pose suite.
        python tools\validate_visual_capture_run.py begin unit00
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=unit00
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify unit00
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="unit02" (
        echo Capturing the complete Unit-02 pose suite.
        python tools\validate_visual_capture_run.py begin unit02
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=unit02
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify unit02
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="mass" (
        echo Capturing Mass Production EVA idle, move, attack, revive, and ritual.
        echo Each state is recorded from seven fixed external views.
        python tools\validate_visual_capture_run.py begin mass
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=mass
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify mass
        if errorlevel 1 exit /b 1
    ) else if "%~2"=="" (
        echo Capturing the complete Unit-01 pose suite.
        python tools\validate_visual_capture_run.py begin unit01
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=unit01
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify unit01
        if errorlevel 1 exit /b 1
    ) else if /i "%~2"=="unit01" (
        echo Capturing the complete Unit-01 pose suite.
        python tools\validate_visual_capture_run.py begin unit01
        if errorlevel 1 exit /b 1
        call gradlew.bat runClient -PquickPlayWorld=%SEELE_VISUAL_WORLD% -PvisualCapture=true -PvisualCaptureUnit=unit01
        if errorlevel 1 exit /b 1
        python tools\validate_visual_capture_run.py verify unit01
        if errorlevel 1 exit /b 1
    ) else (
        echo Unknown visual target "%~2".
        echo Use: visual all, unit01, unit00, unit02, mass, tokyo3, tokyo3_battle, tokyo3_retraction, geofront, geofront_sortie, silo, or impact.
        pause
        exit /b 2
    )
) else (
    rem Local desktop testing is fail-closed: never display the obsolete
    rem fallback body when the active ResourceManager sees a stale/mixed pack.
    rem Keep the huge transparent GeoFront sphere responsive without touching
    rem the strict Tigerar1 EVA mesh or texture path.
    python tools\apply_client_performance_profile.py
    if errorlevel 1 (
        echo SEELE manual performance profile could not be applied.
        pause
        exit /b 1
    )
    if exist "run\saves\SEELE_TOKYO3_REBUILT\level.dat" (
        call gradlew.bat runClient -PstrictHighDetail=true -PquickPlayWorld=SEELE_TOKYO3_REBUILT
    ) else if exist "run\saves\SEELE_TOKYO3_COMPLETE\level.dat" (
        call gradlew.bat runClient -PstrictHighDetail=true -PquickPlayWorld=SEELE_TOKYO3_COMPLETE
    ) else (
        call gradlew.bat runClient -PstrictHighDetail=true
    )
)
pause
