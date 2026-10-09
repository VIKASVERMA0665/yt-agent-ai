@echo off
setlocal
cd /d "%~dp0"
title Bhakti Dhun - Install Daily Automation

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv\Scripts\python.exe not found.
  echo Run the project setup first.
  pause
  exit /b 1
)

set "PY=%CD%\.venv\Scripts\python.exe"
set "RUNNER=%CD%\scheduled_run.py"

echo Installing daily tasks for the current Windows user...
echo 09:00 - Short 1
echo 12:00 - Long video
echo 18:00 - Short 2
echo 21:00 - Short 3
echo.
echo Videos are uploaded automatically after rendering.
echo config.py currently sets VIDEO_PRIVACY to unlisted, so uploads will not be public.
echo.

schtasks /Create /F /SC DAILY /ST 09:00 /TN "BhaktiDhun-Short-0900" /TR "\"%PY%\" \"%RUNNER%\" --video-type shorts --slot short_0900"
if errorlevel 1 goto :failed
schtasks /Create /F /SC DAILY /ST 12:00 /TN "BhaktiDhun-Long-1200" /TR "\"%PY%\" \"%RUNNER%\" --video-type normal --slot long_1200"
if errorlevel 1 goto :failed
schtasks /Create /F /SC DAILY /ST 18:00 /TN "BhaktiDhun-Short-1800" /TR "\"%PY%\" \"%RUNNER%\" --video-type shorts --slot short_1800"
if errorlevel 1 goto :failed
schtasks /Create /F /SC DAILY /ST 21:00 /TN "BhaktiDhun-Short-2100" /TR "\"%PY%\" \"%RUNNER%\" --video-type shorts --slot short_2100"
if errorlevel 1 goto :failed

echo.
echo SUCCESS: Four daily automation tasks were created.
echo Keep the PC powered on and prevent sleep during scheduled times.
echo Check logs folder after each run.
echo To remove tasks, run uninstall_automation.bat.
pause
exit /b 0

:failed
echo.
echo ERROR: Task creation failed. Run this file using Run as administrator if needed.
pause
exit /b 1
