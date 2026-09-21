# -*- coding: utf-8 -*-
"""切换到 选项->控件 页并截图
用法: shot_controls.py <exe> <outdir> <prefix>
"""
import ctypes, ctypes.wintypes as wt, subprocess, time, zlib, struct, sys, os

u32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
EXE = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
PREFIX = sys.argv[3]
os.makedirs(OUT, exist_ok=True)

HWND = wt.HWND
for f, a, r in [('GetClassNameW', [HWND, wt.LPWSTR, ctypes.c_int], None),
                ('GetMenu', [HWND], ctypes.c_void_p),
                ('GetParent', [HWND], HWND),
                ('SendMessageW', [HWND, ctypes.c_uint, ctypes.c_ulonglong, ctypes.c_void_p], ctypes.c_longlong),
                ('PrintWindow', [HWND, wt.HDC, ctypes.c_uint], None),
                ('ShowWindow', [HWND, ctypes.c_int], None),
                ('SetWindowPos', [HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint], None),
                ('InvalidateRect', [HWND, ctypes.c_void_p, ctypes.c_int], None),
                ('UpdateWindow', [HWND], None),
                ('RedrawWindow', [HWND, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint], None)]:
    fn = getattr(u32, f); fn.argtypes = a
    if r:
        fn.restype = r


def cls(h):
    b = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h, b, 256); return b.value


def pid_of(h):
    p = wt.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p)); return p.value


def enum_top(pid):
    res = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, HWND, wt.LPARAM)

    def cb(h, l):
        if pid_of(h) == pid and u32.IsWindowVisible(h):
            res.append(h)
        return True
    u32.EnumWindows(CB(cb), 0); return res


def descendants(hwnd):
    res = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, HWND, wt.LPARAM)

    def cb(h, l):
        res.append(h); return True
    u32.EnumChildWindows(hwnd, CB(cb), 0); return res


def write_png(path, w, h, bgra):
    rows = []
    for y in range(h):
        line = bytearray()
        for x in range(w):
            i = (y * w + x) * 4
            line += bytes((bgra[i + 2], bgra[i + 1], bgra[i]))
        rows.append(b'\x00' + bytes(line))
    raw = b''.join(rows)

    def ch(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                           + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b''))


def capture(hwnd, path):
    r = wt.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return (0, 0)
    hdc = u32.GetWindowDC(hwnd); mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h); gdi32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 3)
    bi = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(ctypes.create_string_buffer(bi)), 0)
    write_png(path, w, h, buf.raw); return (w, h)


log = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s); log.append(s)


proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE))
try:
    main = None
    for _ in range(80):
        time.sleep(0.25)
        for h in enum_top(proc.pid):
            if u32.GetMenu(h):
                main = h; break
        if main:
            break
    u32.PostMessageW(main, 0x0111, 1029, 0)
    dlg = None
    for _ in range(50):
        time.sleep(0.2)
        for h in enum_top(proc.pid):
            if cls(h) == '#32770' and h != main:
                dlg = h; break
        if dlg:
            break
    P('dlg', dlg)

    pages = [h for h in descendants(dlg) if cls(h) == '#32770' and u32.GetParent(h) == dlg]
    P('pages', pages)
    # 找出含 count>10 ListBox 的页面
    target = None
    for pg in pages:
        for h in descendants(pg):
            if 'ListBox' in cls(h) and u32.SendMessageW(h, 0x018B, 0, 0) > 10:
                target = pg
    P('target page', target)
    for pg in pages:
        u32.ShowWindow(pg, 0)
    if target:
        u32.SetWindowPos(target, 0, 737, 342, 471, 420, 0x0040 | 0x0010 | 0x0004)  # NOSIZE NOACTIVATE SHOWWINDOW
        u32.ShowWindow(target, 5)
        u32.ShowWindow(target, 5)
        time.sleep(0.3)
        u32.InvalidateRect(target, None, 1)
        u32.UpdateWindow(target)
        u32.RedrawWindow(target, None, None, 0x0001 | 0x0080 | 0x0100)
        time.sleep(0.8)
        P('page shot', capture(target, os.path.join(OUT, PREFIX + '_page.png')))
        u32.ShowWindow(dlg, 0); u32.ShowWindow(dlg, 5)
        time.sleep(0.5)
        P('dlg shot', capture(dlg, os.path.join(OUT, PREFIX + '_dlg.png')))
    u32.PostMessageW(dlg, 0x0010, 0, 0)
    time.sleep(0.3)
    u32.PostMessageW(main, 0x0010, 0, 0)
    for _ in range(20):
        if proc.poll() is not None:
            break
        time.sleep(0.2)
finally:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    P('exit', proc.returncode)
    open(os.path.join(OUT, PREFIX + '_shot.txt'), 'w', encoding='utf-8').write('\n'.join(log))
