import struct, json, re

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
    return None

rdata = [s for s in secs if s[0] == '.rdata'][0]
_, rva, vsz, raw, rsz = rdata
start, end = raw, raw + rsz

strings = []
p = start
while p < end:
    q = p
    while q < end and d[q] not in (0,):
        q += 1
    if q - p >= 2:
        s = d[p:q]
        # keep mostly-printable runs
        printable = sum(1 for c in s if 32 <= c < 127)
        if printable >= (q - p) * 0.6:
            strings.append((p, q - p, s.decode('latin1')))
        p = q
    p += 1

print('total candidate ANSI strings in .rdata:', len(strings))
with open(r'D:\Desktop\软件汉化\out\ansi_pool.txt', 'w', encoding='utf-8') as f:
    for off, ln, t in strings:
        f.write('0x%06x  rva=0x%06x  len=%-3d  %r\n' % (off, off2rva(off), ln, t))
print('written')
