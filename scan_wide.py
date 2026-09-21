import struct, re, json, sys

SRC = r'C:\Program Files\voidImageViewer\voidImageViewer.exe'
d = open(SRC, 'rb').read()
e = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, e + 4 + 2)[0]
optsize = struct.unpack_from('<H', d, e + 4 + 16)[0]
opt = e + 24
so = opt + optsize
secs = []
for i in range(nsec):
    o = so + i * 40
    name = d[o:o+8].rstrip(b'\0').decode('latin1')
    vsz, va, rsz, raw = struct.unpack_from('<IIII', d, o + 8)
    secs.append((name, va, vsz, raw, rsz))

# scan .rdata for UTF-16LE strings
sec = [s for s in secs if s[0] == '.rdata'][0]
name, va, vsz, raw, rsz = sec
start, end = raw, raw + rsz
print('rdata file range 0x%x-0x%x' % (start, end))

pat = re.compile(rb'(?:[\x20-\x7e\xa0-\xff]\x00){2,}')
out = []
for m in pat.finditer(d, start, end):
    s = m.group()
    try:
        txt = s.decode('utf-16-le')
    except Exception:
        continue
    out.append((m.start(), len(txt), txt))
print('candidate wide strings:', len(out))
json.dump([{'off': o, 'n': n, 't': t} for o, n, t in out],
          open(r'D:\Desktop\软件汉化\out\wide_strings.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
for o, n, t in out:
    print('0x%06x %3d  %r' % (o, n, t))
