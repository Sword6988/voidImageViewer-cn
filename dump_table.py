import struct, json
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
imgbase = struct.unpack_from('<Q', d, opt + 24)[0]
szimage = struct.unpack_from('<I', d, opt + 56)[0]
def rva2off(rva):
    for nm, va, vsz, raw, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
def which(off):
    for nm, va, vsz, raw, rsz in secs:
        if raw <= off < raw + rsz:
            return nm
rows = []
for p in range(0, len(d) - 8):
    v = struct.unpack_from('<Q', d, p)[0]
    if imgbase <= v < imgbase + szimage:
        t = v - imgbase
        if 0x42000 <= t < 0x52000:
            o = rva2off(t)
            if o is None:
                continue
            j = d.index(b'\0', o)
            rows.append((p, which(p), t, d[o:j].decode('utf-8', 'replace')))
rows.sort()
print('abs ptr count', len(rows))
prev = None
for p, sec, t, s in rows:
    gap = '' if prev is None else ('  (+%d)' % (p - prev))
    prev = p
    print('%06x [%s] -> 0x%06x  %r%s' % (p, sec, t, s[:80], gap))
