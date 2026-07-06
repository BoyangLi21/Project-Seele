@echo off
rem Project SEELE - one-click test client.
rem Uses the standalone JDK 17 if JAVA_HOME is not already set to one.
if not defined JAVA_HOME set "JAVA_HOME=C:\Users\liboy\jdks\jdk-17.0.19+10"
cd /d "%~dp0.."
echo Starting Project SEELE test client (first launch takes a minute)...
call gradlew.bat runClient
pause
