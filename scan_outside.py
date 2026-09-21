import struct, re, json
SRC = r'C:\Program Files\voidImageViewer\voidImageViewer.exe'
d = open(SRC, 'rb').read()
e = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, e + 6)[0]
optsize = struct.unpack_from('<H', d, e + 20)[0]
opt = e + 24
so = opt + optsize
secs = []
for k in range(nsec):
    o = so + k * 40
    nm = d[o:o+8].rstrip(b'\0').decode('latin1')
    vsz, va, rsz, raw = struct.unpack_from('<IIII', d, o + 8)
    secs.append((nm, va, vsz, raw, rsz))
def off2rva(off):
    for nm, va, vsz, raw, rsz in secs:
        if raw <= off < raw + rsz:
            return va + (off - raw)

# UI 区间 RVA
UI_LO, UI_HI = 0x431c0, 0x44a00
WORDY = re.compile(r'[A-Za-z]')
out = []
for s in secs:
    nm, va, vsz, raw, rsz = s
    i = raw
    end = raw + rsz
    while i < end:
        j = i
        while j < end and d[j] != 0:
            j += 1
        if 4 <= j - i <= 2000:
            b = d[i:j]
            printable = all(32 <= c < 127 or c in (9, 10, 13) for c in b)
            if printable:
                t = b.decode('ascii')
                if WORDY.search(t) and ' ' in t:
                    out.append((off2rva(i), nm, t))
        i = j + 1
print('全文件「含空格+字母」的NUL结尾串:', len(out))
inside = [x for x in out if UI_LO <= x[0] < UI_HI]
outside = [x for x in out if not (UI_LO <= x[0] < UI_HI)]
print('  UI区间内:', len(inside), ' 区间外:', len(outside))
print('\n=== UI 区间外的可疑 UI 串 ===')
for r, nm, t in outside:
    print('  0x%06x [%s] %r' % (r, nm, t[:110]))
