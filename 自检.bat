@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
title MusicBox Studio - Health Check

echo ============================================================
echo  Health check: search / play-url / download / lyrics / cover
echo  (A failed item affects only that feature; the app still runs)
echo ============================================================
echo.

set PY=
where python >nul 2>nul && set PY=python
if "%PY%"=="" (where py >nul 2>nul && set PY=py -3)
if "%PY%"=="" (
  echo [ERROR] Python not found. Install Python 3.11+ and retry.
  pause
  exit /b 1
)

%PY% tools\healthcheck.py
set RC=%errorlevel%
echo.
if "%RC%"=="0" (
  echo [RESULT] All green - endpoints and cipher are working.
) else (
  echo [RESULT] Some links are broken. See the "fix direction" above,
  echo          then read the maintenance doc under docs\ (endpoint map + fixes).
)
echo.
pause
exit /b %RC%
