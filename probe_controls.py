# -*- coding: utf-8 -*-
"""专查 选项对话框 -> 控件 页 ListBox 的真实内容与显示
用法: probe_controls.py <exe> <outdir> <prefix>
"""
import ctypes, ctypes.wintypes as wt, subprocess, time, zlib, struct, sys, os

u32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
EXE = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
PREFIX = sys.argv[3]
os.makedirs(OUT, exist_ok=True)

for f, a, r in [('GetWindowTextW', [wt.HWND, wt.LPWSTR, ctypes.c_int], None),
                ('GetClassNameW', [wt.HWND, wt.LPWSTR, ctypes.c_int], None),
                ('GetMenu', [wt.HWND], ctypes.c_void_p),
                ('GetParent', [wt.HWND], ctypes.c_void_p),
                ('SendMessageW', [wt.HWND, ctypes.c_uint, ctypes.c_ulonglong, ctypes.c_void_p], ctypes.c_longlong),
                ('PrintWindow', [wt.HWND, wt.HDC, ctypes.c_uint], None),
                ('ShowWindow', [wt.HWND, ctypes.c_int], None),
                ('SetWindowPos', [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint], None)]:
    fn = getattr(u32, f); fn.argtypes = a
    if r:
        fn.restype = r


def text(h):
    b = ctypes.create_unicode_buffer(4096); u32.GetWindowTextW(h, b, 4096); return b.value


def cls(h):
    b = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h, b, 256); return b.value


def pid_of(h):
    p = wt.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p)); return p.value


def enum_top(pid):
    res = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        if pid_of(h) == pid and u32.IsWindowVisible(h):
            res.append(h)
        return True
    u32.EnumWindows(CB(cb), 0); return res


def descendants(hwnd):
    res = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        r = wt.RECT(); u32.GetWindowRect(h, ctypes.byref(r))
        res.append((h, cls(h), text(h), (r.left, r.top, r.right - r.left, r.bottom - r.top),
                    bool(u32.IsWindowVisible(h)), u32.GetParent(h)))
        return True
    u32.EnumChildWindows(hwnd, CB(cb), 0); return res


def raw_bytes_ansi(h, i):
    n = u32.SendMessageW(h, 0x018B, 0, 0)
    if i >= n:
        return b''
    ln = u32.SendMessageW(h, 0x018A, i, 0)
    if ln <= 0:
        return b''
    buf = ctypes.create_string_buffer(ln + 8)
    u32.SendMessageW(h, 0x0189, i, ctypes.cast(buf, ctypes.c_void_p))
    return bytes(buf.raw[:ln])


def raw_bytes_w(h, i):
    n = u32.SendMessageW(h, 0x018B, 0, 0)
    if i >= n:
        return b''
    ln = u32.SendMessageW(h, 0x019A, i, 0)
    if ln <= 0:
        return b''
    buf = ctypes.create_string_buffer((ln + 8) * 2)
    u32.SendMessageW(h, 0x0199, i, ctypes.cast(buf, ctypes.c_void_p))
    return bytes(buf.raw[:(ln + 1) * 2])


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
    u32.PrintWindow(hwnd, mdc, 2)
    bi = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(ctypes.create_string_buffer(bi)), 0)
    write_png(path, w, h, buf.raw); return (w, h)


lines = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s); lines.append(s)


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
    P('主窗口:', text(main), main)
    u32.PostMessageW(main, 0x0111, 1029, 0)  # 选项(&O)...
    dlg = None
    for _ in range(50):
        time.sleep(0.2)
        for h in enum_top(proc.pid):
            if cls(h) == '#32770' and h != main:
                dlg = h; break
        if dlg:
            break
    P('对话框:', text(dlg), dlg)
    P('--- 全部子孙窗口 ---')
    ds = descendants(dlg)
    for h, c, t, rc, vis, par in ds:
        cnt = ''
        if 'ListBox' in c:
            cnt = ' count=%d' % u32.SendMessageW(h, 0x018B, 0, 0)
        P('  h=%d par=%d vis=%d %-22s %-8s %r%s' % (h, par, vis, c, str(rc), t[:60], cnt))

    # 找 count 最大的 ListBox
    lb = None; best = 0
    for h, c, t, rc, vis, par in ds:
        if 'ListBox' in c:
            n = u32.SendMessageW(h, 0x018B, 0, 0)
            if n > best:
                best = n; lb = h
    P('命令列表 ListBox =', lb, 'items =', best)
    if lb:
        P('  ANSI(0x0189) raw[0] =', raw_bytes_ansi(lb, 0))
        P('  WIDE(0x0199) raw[0] =', raw_bytes_w(lb, 0))
        nb = raw_bytes_ansi(lb, 0)
        P('  ansi utf8   :', repr(nb.decode('utf-8', 'replace')[:60]))
        P('  ansi cp936  :', repr(nb.decode('gbk', 'replace')[:60]))
        # 把该 ListBox 所在页显示到最前，然后截图
        page = u32.GetParent(lb)
        P('  page hwnd =', page, cls(page))
        u32.ShowWindow(page, 5)
        u32.SetWindowPos(page, -1, 0, 0, 0, 0, 0x0043)  # HWND_TOP|NOSIZE|NOMOVE|SHOWWINDOW
        time.sleep(0.6)
        P('  对话框截图:', capture(dlg, os.path.join(OUT, PREFIX + '_dlg_controls.png')))
        P('  页面截图:', capture(page, os.path.join(OUT, PREFIX + '_page_controls.png')))
        P('  列表截图:', capture(lb, os.path.join(OUT, PREFIX + '_listbox.png')))
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
    P('exit =', proc.returncode)
    open(os.path.join(OUT, PREFIX + '_controls.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
