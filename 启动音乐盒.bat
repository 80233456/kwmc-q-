@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
title MusicBox Studio

rem 1) 优先用打包好的独立程序（无需 Python）
if exist "dist\音乐盒Studio\音乐盒Studio.exe" (
  start "" "dist\音乐盒Studio\音乐盒Studio.exe"
  exit /b 0
)

rem 2) 否则用 Python 运行（开发态）
where pythonw >nul 2>nul
if not errorlevel 1 (
  start "" pythonw kuwo_app.py
  exit /b 0
)
where python >nul 2>nul
if not errorlevel 1 (
  python kuwo_app.py
  set RC=%errorlevel%
  if not "%RC%"=="0" echo. & echo (exited with code %RC%) & pause
  exit /b %RC%
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 kuwo_app.py
  set RC=%errorlevel%
  if not "%RC%"=="0" echo. & echo (exited with code %RC%) & pause
  exit /b %RC%
)

echo [ERROR] Neither the packaged app nor Python 3 was found.
echo         打包版应位于: dist\音乐盒Studio\音乐盒Studio.exe
pause
exit /b 1
