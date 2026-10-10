@echo off
setlocal
cd /d "%~dp0"
title Bhakti Dhun - Start Automation

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv\Scripts\python.exe not found.
  echo Open the project folder and finish setup first.
  pause
  exit /b 1
)

echo ============================================================
echo Bhakti Dhun automatic video creation and YouTube upload
echo ============================================================
echo.
echo This will:
echo 1. Ensure daily scheduled tasks are installed.
echo 2. Start a NEW Short now and automatically upload it after rendering.
echo 3. Keep daily schedule: 09:00 Short, 12:00 Long, 18:00 Short, 21:00 Short.
echo.
echo Requirements: PC on and awake, internet available, valid API/OAuth credentials.
echo Upload privacy is currently UNLISTED in config.py.
echo.
choice /C YN /M "Start now"
if errorlevel 2 exit /b 0

echo.
echo [1/2] Installing/updating daily scheduled tasks...
call "%~dp0install_automation.bat"
if errorlevel 1 (
  echo.
  echo ERROR: Scheduled task setup failed. See message above.
  pause
  exit /b 1
)

echo.
echo [2/2] Starting a fresh Short now. This run will render and auto-upload.
echo Keep this window open until the log says AUTO-UPLOAD SUCCESS.
"%~dp0.venv\Scripts\python.exe" "%~dp0scheduled_run.py" --video-type shorts --slot one_click_start
if errorlevel 1 (
  echo.
  echo The run failed. Check logs\ for the one_click_start log and share the error.
  pause
  exit /b 1
)

echo.
echo The immediate run has finished. Future videos run at the scheduled times.
pause
