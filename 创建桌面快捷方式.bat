@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Create Desktop Shortcut - MusicBox Studio
set TARGET=%~dp0dist\MusicBox\MusicBox.exe
if not exist "%TARGET%" set TARGET=%~dp0dist\音乐盒Studio\音乐盒Studio.exe
if not exist "%TARGET%" (
  echo [ERROR] Packaged app not found. Build it first:
  echo         python -m PyInstaller --noconfirm --clean --windowed --name "音乐盒Studio" ^
  echo           --icon appicon.ico --add-data "appicon.ico;." kuwo_app.py
  pause
  exit /b 1
)
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\音乐盒 Studio.lnk');" ^
  "$s.TargetPath='%TARGET%';" ^
  "$s.WorkingDirectory=Split-Path '%TARGET%';" ^
  "$s.IconLocation='%~dp0appicon.ico';" ^
  "$s.Description='音乐盒 Studio - 搜索/试听/无损下载';" ^
  "$s.Save()"
echo.
echo Done. Shortcut created on Desktop: 音乐盒 Studio
pause
