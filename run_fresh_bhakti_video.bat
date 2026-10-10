@echo off
setlocal
cd /d "%~dp0"
title YT Agent AI - Fresh Radha Krishna Bhakti Video

echo.
echo ==========================================
echo   Fresh Radha-Krishna Bhakti Video
echo   Swara Hindi Female voice
echo ==========================================
echo.

where git >nul 2>nul
if %errorlevel%==0 (
  echo [1/2] Updating latest project files...
  git pull origin main
  if errorlevel 1 (
    echo.
    echo Git pull failed. Resolve the Git message above, then run this file again.
    pause
    exit /b 1
  )
) else (
  echo Git is not installed or not in PATH. Using current local files.
)

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
  set "PYTHON_EXE=python"
)

echo.
echo [2/2] Generating a fresh video. This can take several minutes.
echo This run will NOT upload to YouTube automatically.
echo.

"%PYTHON_EXE%" pipeline.py --topic "राधा-कृष्ण की दिव्य प्रेम भक्ति, वृंदावन की सुंदर लीलाएँ और भगवान श्रीकृष्ण का जीवन बदलने वाला संदेश" --voice hi-IN-SwaraNeural --no-review

if errorlevel 1 (
  echo.
  echo Video generation failed. Read the error above and share a screenshot.
) else (
  echo.
  echo Done. Open the newest output\auto_*_normal\final_video.mp4 folder.
)
pause
endlocal
