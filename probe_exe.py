# -*- coding: utf-8 -*-
"""通用运行时取证：probe_exe.py <exe> <outdir> <prefix> [img1 img2 ...]"""
import ctypes, ctypes.wintypes as wt, subprocess, time, zlib, struct, sys, os

u32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
EXE = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
PREFIX = sys.argv[3]
IMGS = sys.argv[4:]
os.makedirs(OUT, exist_ok=True)

for f, a, r in [('GetWindowTextW', [wt.HWND, wt.LPWSTR, ctypes.c_int], None),
                ('GetClassNameW', [wt.HWND, wt.LPWSTR, ctypes.c_int], None),
                ('GetMenuStringW', [wt.HMENU, ctypes.c_uint, wt.LPWSTR, ctypes.c_int, ctypes.c_uint], None),
                ('GetMenu', [wt.HWND], ctypes.c_void_p),
                ('GetSubMenu', [ctypes.c_void_p, ctypes.c_int], ctypes.c_void_p),
                ('GetMenuItemCount', [ctypes.c_void_p], ctypes.c_int),
                ('GetMenuItemID', [ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
                ('SendMessageW', [wt.HWND, ctypes.c_uint, ctypes.c_ulonglong, ctypes.c_void_p], ctypes.c_longlong),
                ('PrintWindow', [wt.HWND, wt.HDC, ctypes.c_uint], None)]:
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


def kids(hwnd):
    res = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

    def cb(h, l):
        res.append((cls(h), text(h), h)); return True
    u32.EnumChildWindows(hwnd, CB(cb), 0); return res


def extra(h, c):
    v = []
    try:
        if 'ComboBox' in c:
            n = u32.SendMessageW(h, 0x0146, 0, 0)
            for i in range(n):
                ln = u32.SendMessageW(h, 0x0149, i, 0)
                if ln <= 0:
                    continue
                b = ctypes.create_unicode_buffer(ln + 2)
                u32.SendMessageW(h, 0x0148, i, ctypes.cast(b, ctypes.c_void_p)); v.append(b.value)
        elif 'ListBox' in c and 'ListView' not in c:
            n = u32.SendMessageW(h, 0x018B, 0, 0)
            for i in range(min(n, 120)):
                ln = u32.SendMessageW(h, 0x018A, i, 0)
                if ln <= 0:
                    continue
                b = ctypes.create_unicode_buffer(ln + 2)
                u32.SendMessageW(h, 0x0189, i, ctypes.cast(b, ctypes.c_void_p)); v.append(b.value)
    except Exception as ex:
        v.append('ERR %s' % ex)
    return v


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


IDMAP = {}


def dump_menu(hm, depth=0, out=None):
    if out is None:
        out = []
    for i in range(u32.GetMenuItemCount(hm)):
        b = ctypes.create_unicode_buffer(512); u32.GetMenuStringW(hm, i, b, 512, 0x400)
        sub = u32.GetSubMenu(hm, i); mid = u32.GetMenuItemID(hm, i)
        if not sub:
            out.append(('  ' * depth) + b.value + '  {id=%d}' % mid)
            IDMAP.setdefault(b.value.split('\t')[0], mid)
        else:
            out.append(('  ' * depth) + b.value)
            dump_menu(sub, depth + 1, out)
    return out


proc = subprocess.Popen([EXE] + IMGS, cwd=os.path.dirname(EXE))
lines = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s); lines.append(s)

P('PID', proc.pid, 'EXE', EXE)
main = None
try:
    for _ in range(80):
        time.sleep(0.25)
        for h in enum_top(proc.pid):
            if u32.GetMenu(h):
                main = h; break
        if main:
            break
    if not main:
        P('!! 未找到主窗口'); sys.exit(1)
    P('主窗口标题:', text(main))
    P('--- 子控件 ---')
    for c, t, h in kids(main):
        P('   [%s] %r' % (c, t))
    P('===== 菜单栏 =====')
    for l in dump_menu(u32.GetMenu(main)):
        P(l)
    P('--- 截图 ---', capture(main, os.path.join(OUT, PREFIX + '_main.png')))

    for label, tag in [('选项(&O)...', 'options'), ('\u5173\u4e8e(&A)', 'about'),
                       ('&Options...', 'options'), ('&About', 'about'),
                       ('命令行选项(&C)', 'cmdline'), ('&Command Line Options', 'cmdline'),
                       ('\u91cd\u547d\u540d(&M)', 'rename'), ('&Rename', 'rename'),
                       ('\u8df3\u8f6c\u5230(&J)...', 'jumpto'), ('&Jump To...', 'jumpto')]:
        if label not in IDMAP:
            continue
        u32.PostMessageW(main, 0x0111, IDMAP[label], 0)
        dlg = None
        for _ in range(40):
            time.sleep(0.2)
            for h in enum_top(proc.pid):
                if cls(h) == '#32770' and h != main:
                    dlg = h; break
            if dlg:
                break
        if dlg:
            P('\n=== DIALOG %s : %s ===' % (tag, text(dlg)))
            for c, t, h in kids(dlg):
                e = extra(h, c)
                if t.strip() or e:
                    P('   [%s] %r  %s' % (c, t, ('<= ' + repr(e)) if e else ''))
            time.sleep(0.5)
            P('   截图:', capture(dlg, os.path.join(OUT, '%s_dlg_%s.png' % (PREFIX, tag))))
            u32.PostMessageW(dlg, 0x0010, 0, 0)
        time.sleep(0.35)
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
    P('进程结束 exit =', proc.returncode)
    open(os.path.join(OUT, PREFIX + '_probe.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
