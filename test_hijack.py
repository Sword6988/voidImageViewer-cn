# -*- coding: utf-8 -*-
"""实测：exe 目录放置 COMCTL32.dll 能否劫持导入（.local 重定向是否生效）。

对照实验：
  A) 仅放伪造 COMCTL32.dll（无 .local）      -> 预期：程序照常启动（劫持失败）
  B) 放伪造 COMCTL32.dll + voidImageViewer.exe.local -> 预期：启动失败（劫持成功）
判定依据：进程是否存活 3 秒 + 是否存在属于该进程的顶层窗口。
"""
import ctypes
import ctypes.wintypes as wt
import os
import shutil
import subprocess
import sys
import time

u32 = ctypes.WinDLL("user32", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)

u32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
u32.EnumWindows.restype = wt.BOOL
u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
u32.GetWindowThreadProcessId.restype = wt.DWORD
u32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.IsWindowVisible.argtypes = [wt.HWND]
u32.IsWindowVisible.restype = wt.BOOL
u32.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT, ctypes.POINTER(ctypes.c_void_p)]
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE

SRC = r"D:\Desktop\软件汉化\backup\voidImageViewer.exe.orig"
BASE = r"D:\Desktop\软件汉化\out\dll_hijack_test"

WIN_ENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def windows_of(pid):
    found = []

    def cb(hwnd, _):
        p = wt.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid:
            cls = ctypes.create_unicode_buffer(256)
            u32.GetClassNameW(hwnd, cls, 256)
            txt = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, txt, 256)
            found.append((hwnd, cls.value, txt.value, bool(u32.IsWindowVisible(hwnd))))
        return True

    u32.EnumWindows(WIN_ENUM(cb), 0)
    return found


def run_case(name, with_local):
    d = os.path.join(BASE, name)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    exe = os.path.join(d, "voidImageViewer.exe")
    shutil.copy2(SRC, exe)
    with open(os.path.join(d, "COMCTL32.dll"), "wb") as f:
        f.write(b"THIS IS NOT A REAL DLL - hijack probe\x00")
    if with_local:
        open(os.path.join(d, "voidImageViewer.exe.local"), "wb").close()

    # 抑制子进程继承的硬错误弹窗
    k32.SetErrorMode(0x8003)

    si = subprocess.STARTUPINFO()
    si.dwFlags = subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    p = subprocess.Popen([exe], cwd=d, startupinfo=si,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3.0)
    rc = p.poll()
    alive = rc is None
    wins = windows_of(p.pid)
    if alive:
        try:
            p.terminate()
        except Exception:
            pass
        time.sleep(0.6)
        if p.poll() is None:
            subprocess.run(["taskkill", "/F", "/PID", str(p.pid)],
                           capture_output=True)
    verdict = ("启动成功(窗口已创建) -> 劫持未生效" if wins
               else ("进程退出 code=%s 且无窗口 -> 劫持生效(加载器拒绝了伪造 DLL)" % rc
                     if not alive else "进程存活但无窗口 -> 结果不明确"))
    print("[%s] .local=%-5s alive=%-5s rc=%-6s windows=%d" % (name, with_local, alive, rc, len(wins)))
    for h, cls, t, vis in wins:
        print("      hwnd=%#x class=%r title=%r visible=%s" % (h, cls, t, vis))
    print("      判定: %s" % verdict)
    return verdict


if __name__ == "__main__":
    print("=== 对照实验：exe 目录 COMCTL32.dll 劫持 ===")
    run_case("no_local", False)
    print()
    run_case("with_local", True)
