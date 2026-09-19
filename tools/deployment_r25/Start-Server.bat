@echo off
setlocal
cd /d "%~dp0"
if not exist "libraries\net\minecraftforge\forge\1.20.1-47.4.10\win_args.txt" (
 echo Run Install-Server.bat first.
 pause
 exit /b 1
)
if not exist "SEELE_TV_WORLD_PREVIEW_20260906\r25_ready.json" (
 echo Import the R25 world ZIP into SEELE_TV_WORLD_PREVIEW_20260906 first.
 pause
 exit /b 1
)
set "SEELE_JAVA=java"
if defined JAVA_HOME set "SEELE_JAVA=%JAVA_HOME%\bin\java.exe"
"%SEELE_JAVA%" @user_jvm_args.txt @libraries/net/minecraftforge/forge/1.20.1-47.4.10/win_args.txt nogui
set "SEELE_EXIT=%ERRORLEVEL%"
pause
exit /b %SEELE_EXIT%
