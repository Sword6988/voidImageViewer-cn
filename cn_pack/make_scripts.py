# -*- coding: utf-8 -*-
"""生成汉化包里的 .bat（GBK 编码）与说明文本。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

BAT_COMMON = r"""@echo off
chcp 936 >nul
title Void Image Viewer 汉化包
cd /d "%~dp0"
setlocal

set "PY="
if exist "%~dp0runtime\python.exe" set "PY=%~dp0runtime\python.exe"
if not defined PY if exist "C:\Users\Shibeng\.workbuddy\binaries\python\envs\default\Scripts\python.exe" set "PY=C:\Users\Shibeng\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not defined PY if exist "C:\Users\Shibeng\.workbuddy\binaries\python\versions\3.13.12\python.exe" set "PY=C:\Users\Shibeng\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not defined PY for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY (
  echo.
  echo   [X] 未找到 Python 解释器。
  echo       请安装 Python 3.8+ 后重试，或把 python.exe 放到本目录 runtime\ 子目录下。
  echo.
  pause
  exit /b 1
)
"""

BAT_APPLY = BAT_COMMON + r"""
echo.
echo  ============================================================
echo    Void Image Viewer 汉化包  ^|  一键汉化
echo    解释器 : %PY%
echo    目标   : C:\Program Files\voidImageViewer\voidImageViewer.exe
echo  ============================================================
echo.
"%PY%" "%~dp0rebuild_cn.py" --deploy --verify %*
echo.
pause
"""

BAT_BUILD = BAT_COMMON + r"""
echo.
echo  ============================================================
echo    Void Image Viewer 汉化包  ^|  仅生成（不动安装目录）
echo    解释器 : %PY%
echo  ============================================================
echo.
"%PY%" "%~dp0rebuild_cn.py" %*
echo.
pause
"""

BAT_RESTORE = BAT_COMMON + r"""
echo.
echo  ============================================================
echo    Void Image Viewer 汉化包  ^|  还原原始程序
echo  ============================================================
echo.
"%PY%" "%~dp0rebuild_cn.py" --restore %*
echo.
pause
"""

MANUAL = u"""Void Image Viewer 汉化包 v1.0
================================================================
作用：把「安装目录里的原版 voidImageViewer.exe」重新生成为汉化版。
特点：不依赖硬编码地址，程序小版本升级后一般无需修改本包即可重新生成。

----------------------------------------------------------------
【目录内容】
  汉化.bat          一键汉化（自动备份 -> 生成 -> 覆盖 -> 启动自检）
  仅生成.bat        只生成 cn_out\\voidImageViewer.cn.exe，不动安装目录
  还原.bat          从 备份\\ 里把原始 exe 还原回去
  rebuild_cn.py     版本自适应重建器（核心）
  translations.py   翻译表（原文 -> 中文译文，按文本内容匹配，与版本无关）
  pe_res_engine.py  PE 解析与资源重建引擎
  备份\\            每次汉化前自动保存的原版 exe
  cn_out\\          生成的汉化版 exe

----------------------------------------------------------------
【日常使用（程序升级后）】
  第 1 步  正常下载安装新版本 voidImageViewer
  第 2 步  双击本目录的  汉化.bat
  第 3 步  看到「自检结论：菜单已为中文」即完成

  如果不想用脚本，也可以手动：
     把 cn_out\\voidImageViewer.cn.exe 复制到
     C:\\Program Files\\voidImageViewer\\ 覆盖 voidImageViewer.exe
  （注意：必须先跑过一次 仅生成.bat 或 汉化.bat 才会产生该文件；
    且覆盖前请自行保留原版。）

----------------------------------------------------------------
【需要的环境】
  Python 3.8 及以上，且本脚本只用标准库（无需 pip 安装任何东西）。
  若双击报「未找到 Python 解释器」，请安装 Python 后重试，
  或把 python.exe 放到本目录的 runtime\\ 子目录下。

----------------------------------------------------------------
【注意事项】
  1. 写入 C:\\Program Files 需要管理员权限。若报权限错误，
     请右键 汉化.bat ->「以管理员身份运行」。
  2. 汉化.bat 会先把安装目录里的 exe 备份到 备份\\，再覆盖。
     想退回英文版：双击 还原.bat。
  3. 覆盖后程序失去原 Authenticode 数字签名（签名段被原样搬移，
     但内容已变，签名不再有效）。若你的杀软/EDR 对未签名程序告警，
     属正常现象，请自行加白名单或改用 仅生成.bat + 手动替换。
  4. 程序会把快捷键等设置写入 %APPDATA%\\voidImageViewer\\voidImageViewer.ini，
     键名由命令名派生；汉化后少数组名可能重名，但快捷键取值不受影响。
  5. 若目标 exe 已经是汉化版（含 .cnstr 节），本包会自动改用
     备份\\ 里的原版重新生成。因此可以重复双击 汉化.bat。
"""

if __name__ == "__main__":
    for fn, txt in (("汉化.bat", BAT_APPLY),
                    ("仅生成.bat", BAT_BUILD),
                    ("还原.bat", BAT_RESTORE)):
        p = os.path.join(HERE, fn)
        with open(p, "w", encoding="gbk", newline="\r\n") as f:
            f.write(txt)
        print("写出 %s (%d 字节, GBK)" % (p, os.path.getsize(p)))
    p = os.path.join(HERE, "使用说明.txt")
    with open(p, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(MANUAL)
    print("写出 %s (%d 字节, UTF-8-BOM)" % (p, os.path.getsize(p)))
