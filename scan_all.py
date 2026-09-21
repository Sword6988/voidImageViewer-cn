import re, json, struct

SRC = r'C:\Program Files\voidImageViewer\voidImageViewer.exe'
d = open(SRC, 'rb').read()
n = len(d)

# loose scan: any UTF-16LE run of >=4 printable-ish chars
res = []
i = 0
buf = []
startpos = None
def flush():
    global buf, startpos
    if buf and len(buf) >= 4:
        res.append((startpos, ''.join(buf)))
    buf = []
    startpos = None

i = 0
while i + 1 < n:
    lo, hi = d[i], d[i+1]
    ch = lo | (hi << 8)
    if (0x20 <= ch <= 0x7e) or (0xa0 <= ch <= 0x2fff) or (0x4e00 <= ch <= 0x9fff) or ch in (9, 10, 13):
        if not buf:
            startpos = i
        buf.append(chr(ch))
        i += 2
    else:
        flush()
        i += 1
flush()

json.dump([{'off': o, 'n': len(t), 't': t} for o, t in res],
          open(r'D:\Desktop\软件汉化\out\wide_all.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('runs:', len(res))
# group by section
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
    secs.append((nm, raw, rsz))
def which(off):
    for nm, raw, rsz in secs:
        if raw <= off < raw + rsz:
            return nm
    return '?'
from collections import Counter
print(Counter(which(o) for o, t in res))
