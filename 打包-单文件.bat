@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
title Build MusicBox Studio (single-file exe)

echo ============================================================
echo  打包单文件版：dist\音乐盒Studio-单文件版.exe
echo  （一个文件，拷到别的电脑直接双击运行，无需 Python）
echo ============================================================
echo.

where python >nul 2>nul || (echo [ERROR] 未找到 python，请先安装 Python 3.11+ & pause & exit /b 1)

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "音乐盒Studio-单文件版" ^
  --icon appicon.ico --add-data "appicon.ico;." ^
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.Qt3DCore --exclude-module PySide6.QtCharts ^
  --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml ^
  --exclude-module tkinter --exclude-module matplotlib --exclude-module numpy ^
  kuwo_app.py
if errorlevel 1 (echo. & echo [FAILED] 打包失败，请看上面的报错 & pause & exit /b 1)

echo.
echo [OK] 产物：dist\音乐盒Studio-单文件版.exe
for %%F in ("dist\音乐盒Studio-单文件版.exe") do echo      大小：%%~zF 字节
echo.
echo 提示：首次启动约 3-8 秒（自解压到临时目录），之后很快。
pause
