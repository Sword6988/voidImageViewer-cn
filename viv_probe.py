# -*- coding: utf-8 -*-
"""voidImageViewer 运行时取证：菜单栏递归枚举 + 截图 + 对话框抓取"""
import ctypes, ctypes.wintypes as wt, subprocess, time, zlib, struct, sys, os, json

u32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

INST = r"C:\Program Files\voidImageViewer"
EXE = os.path.join(INST, "voidImageViewer.exe")
OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\Desktop\软件汉化\out\runtime"
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "en"
os.makedirs(OUT, exist_ok=True)

u32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
u32.GetMenuStringW.argtypes = [wt.HMENU, ctypes.c_uint, wt.LPWSTR, ctypes.c_int, ctypes.c_uint]
u32.GetMenu.argtypes = [wt.HWND]; u32.GetMenu.restype = ctypes.c_void_p
u32.GetSubMenu.restype = ctypes.c_void_p
u32.GetMenuItemCount.restype = ctypes.c_int
u32.SendMessageW.restype = ctypes.c_longlong
u32.SendMessageW.argtypes = [wt.HWND, ctypes.c_uint, ctypes.c_ulonglong, ctypes.c_void_p]
u32.GetMenuItemID.argtypes = [wt.HMENU, ctypes.c_int]
u32.GetSubMenu.argtypes = [wt.HMENU, ctypes.c_int]
u32.GetMenuItemCount.argtypes = [wt.HMENU]
u32.PrintWindow.argtypes = [wt.HWND, wt.HDC, ctypes.c_uint]
u32.GetWindowDC.argtypes = [wt.HWND]
u32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
gdi32.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
gdi32.GetDIBits.argtypes = [wt.HDC, wt.HBITMAP, ctypes.c_uint, ctypes.c_uint,
                            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]


def text(hwnd):
    b = ctypes.create_unicode_buffer(2048)
    u32.GetWindowTextW(hwnd, b, 2048)
    return b.value


def cls(hwnd):
    b = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, b, 256)
    return b.value


def pid_of(hwnd):
    p = wt.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    return p.value


def enum_top(pid, visible=True):
    res = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        if pid_of(h) == pid and (u32.IsWindowVisible(h) or not visible):
            res.append(h)
        return True
    u32.EnumWindows(CB(cb), 0)
    return res


def children(hwnd, depth=0):
    res = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        res.append((depth, cls(h), text(h), h))
        return True
    u32.EnumChildWindows(hwnd, CB(cb), 0)
    return res


def write_png(path, w, h, bgra):
    rows = []
    for y in range(h):
        line = bytearray()
        for x in range(w):
            i = (y * w + x) * 4
            line += bytes((bgra[i + 2], bgra[i + 1], bgra[i]))
        rows.append(b'\x00' + bytes(line))
    raw = b''.join(rows)

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 6))
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)


def capture(hwnd, path):
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return (0, 0)
    hdc = u32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    u32.PrintWindow(hwnd, mdc, 2)
    bi = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(ctypes.create_string_buffer(bi)), 0)
    write_png(path, w, h, buf.raw)
    return (w, h)


IDMAP = {}


def dump_menu(hmenu, depth=0, out=None):
    if out is None:
        out = []
    n = u32.GetMenuItemCount(hmenu)
    for i in range(n):
        b = ctypes.create_unicode_buffer(512)
        u32.GetMenuStringW(hmenu, i, b, 512, 0x400)
        mid = u32.GetMenuItemID(hmenu, i)
        sub = u32.GetSubMenu(hmenu, i)
        label = b.value.split('\t')[0]
        if sub is None:
            out.append(('  ' * depth) + b.value + '  {id=%d}' % mid)
            IDMAP.setdefault(label, mid)
        else:
            out.append(('  ' * depth) + b.value)
            dump_menu(sub, depth + 1, out)
    return out


def extra_values(hh, clsname):
    """读取 ComboBox / ListBox 的条目文本"""
    vals = []
    try:
        if 'ComboBox' in clsname:
            n = u32.SendMessageW(hh, 0x0146, 0, 0)      # CB_GETCOUNT
            for i in range(n):
                ln = u32.SendMessageW(hh, 0x0149, i, 0)  # CB_GETLBTEXTLEN
                if ln <= 0:
                    continue
                buf = ctypes.create_unicode_buffer(ln + 2)
                u32.SendMessageW(hh, 0x0148, i, ctypes.cast(buf, ctypes.c_void_p))  # CB_GETLBTEXT
                vals.append(buf.value)
        elif 'ListBox' in clsname and 'ListView' not in clsname:
            n = u32.SendMessageW(hh, 0x018B, 0, 0)      # LB_GETCOUNT
            for i in range(n):
                ln = u32.SendMessageW(hh, 0x018A, i, 0)  # LB_GETTEXTLEN
                if ln <= 0:
                    continue
                buf = ctypes.create_unicode_buffer(ln + 2)
                u32.SendMessageW(hh, 0x0189, i, ctypes.cast(buf, ctypes.c_void_p))
                vals.append(buf.value)
    except Exception as e:
        vals.append('ERR %s' % e)
    return vals


proc = subprocess.Popen([EXE], cwd=INST)
print("PID =", proc.pid)
main = None
try:
    for _ in range(60):
        time.sleep(0.25)
        for h in enum_top(proc.pid):
            if u32.GetMenu(h):
                main = h
                break
        if main:
            break
    if not main:
        print("!! no main window"); sys.exit(1)
    print("主窗口标题 :", text(main), " class =", cls(main))

    hmenu = u32.GetMenu(main)
    lines = dump_menu(hmenu)
    print("\n===== 菜单栏（原文）=====")
    for l in lines:
        print(l)
    open(os.path.join(OUT, '%s_menu.txt' % PREFIX), 'w', encoding='utf-8').write('\n'.join(lines))

    time.sleep(0.6)
    print("\n主窗口截图:", capture(main, os.path.join(OUT, '%s_main.png' % PREFIX)))

    # 抓取各对话框
    def trig(label, tag):
        mid = IDMAP.get(label)
        if mid is None:
            print('!! IDMAP miss:', label, '(have %d entries)' % len(IDMAP))
            return
        u32.PostMessageW(main, 0x0111, mid, 0)
        dlg = None
        for _ in range(40):
            time.sleep(0.2)
            for h in enum_top(proc.pid):
                if cls(h) == '#32770' and h != main:
                    dlg = h
                    break
            if dlg:
                break
        if dlg:
            print('\n=== DIALOG %s : %s ===' % (tag, text(dlg)))
            kids = children(dlg)
            for d, c, tt, hh in kids:
                line = '   [%s] %r' % (c, tt)
                extra = extra_values(hh, c)
                if extra:
                    line += '  <= ' + repr(extra)
                if tt.strip() or extra:
                    print(line)
            open(os.path.join(OUT, '%s_dlg_%s.txt' % (PREFIX, tag)), 'w', encoding='utf-8').write(
                text(dlg) + '\n' + '\n'.join('[%s] %s %r' % (c, tt, extra_values(hh, c)) for d, c, tt, hh in kids))
            time.sleep(0.5)
            print('   截图:', capture(dlg, os.path.join(OUT, '%s_dlg_%s.png' % (PREFIX, tag))))
            u32.PostMessageW(dlg, 0x0010, 0, 0)
        else:
            print('!! no dialog for', tag)
        time.sleep(0.4)

    for label, tag in [('&Options...', 'options'), ('&Rename', 'rename'),
                       ('&About', 'about'), ('&Command Line Options', 'cmdline'),
                       ('&Jump To...', 'jumpto')]:
        trig(label, tag)

    u32.PostMessageW(main, 0x0010, 0, 0)
    for _ in range(20):
        if proc.poll() is not None:
            break
        time.sleep(0.25)
finally:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    print("\n进程结束, exit =", proc.returncode)
