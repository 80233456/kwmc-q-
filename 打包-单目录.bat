@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
title Build MusicBox Studio (folder, one-dir)

echo ============================================================
echo  打包单目录版：dist\音乐盒Studio\  （exe + _internal 一整套）
echo  注意：发给别人时必须把"整个文件夹"打包发送，只发 exe 会报
echo        Failed to load Python DLL ... python311.dll
echo ============================================================
echo.

where python >nul 2>nul || (echo [ERROR] 未找到 python & pause & exit /b 1)

python -m PyInstaller --noconfirm --clean --windowed ^
  --name "音乐盒Studio" ^
  --icon appicon.ico --add-data "appicon.ico;." ^
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.Qt3DCore --exclude-module PySide6.QtCharts ^
  --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml ^
  --exclude-module tkinter --exclude-module matplotlib --exclude-module numpy ^
  kuwo_app.py
if errorlevel 1 (echo. & echo [FAILED] 打包失败 & pause & exit /b 1)

echo.
echo [OK] 产物：dist\音乐盒Studio\
echo      现在把整个文件夹压缩，发给别人：
echo        powershell -Command "Compress-Archive -Path 'dist\音乐盒Studio\*' -DestinationPath 'dist\音乐盒Studio-单目录版.zip' -Force"
pause
