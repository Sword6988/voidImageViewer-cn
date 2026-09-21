@echo off
chcp 936 >nul
title Void Image Viewer 汉化包
cd /d "%~dp0"
setlocal

set "PY="
if exist "%~dp0runtime\python.exe" set "PY=%~dp0runtime\python.exe"
if not defined PY for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY for /f "delims=" %%i in ('where py 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY (
  echo.
  echo   [X] 未找到 Python 解释器。
  echo       请安装 Python 3.8+ 后重试，或把 python.exe 放到本目录 runtime\ 子目录下。
  echo.
  pause
  exit /b 1
)

echo.
echo  ============================================================
echo    Void Image Viewer 汉化包  ^|  还原原始程序
echo  ============================================================
echo.
"%PY%" "%~dp0rebuild_cn.py" --restore %*
echo.
pause
