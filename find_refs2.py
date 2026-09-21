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
def off2rva(off):
    for nm, va, vsz, raw, rsz in secs:
        if raw <= off < raw + rsz:
            return va + (off - raw)
def rva2off(rva):
    for nm, va, vsz, raw, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
def which(off):
    for nm, va, vsz, raw, rsz in secs:
        if raw <= off < raw + rsz:
            return nm
imgbase = struct.unpack_from('<Q', d, opt + 24)[0]
dllchar = struct.unpack_from('<H', d, opt + 70)[0]

print('ImageBase', hex(imgbase), 'DllCharacteristics', hex(dllchar))
print('has .reloc:', any(s[0] == '.reloc' for s in secs))

# --- 全部字符串（NUL 结尾） 用于建立 rva->text
STR_LO, STR_HI = 0x42000, 0x52000   # 全 .rdata
texts = {}
p = 0
rdata = [s for s in secs if s[0] == '.rdata'][0]
_, rva0, vsz0, raw0, rsz0 = rdata
i = raw0
while i < raw0 + rsz0:
    j = i
    while j < raw0 + rsz0 and d[j] != 0:
        j += 1
    if 2 <= j - i <= 3000:
        texts[off2rva(i)] = d[i:j].decode('utf-8', 'replace')
    i = j + 1

# --- 绝对指针
print('\n===== 绝对指针（.data/.rdata 中的 8 字节 ImageBase+RVA）=====')
absp = {}
for p in range(0, len(d) - 8):
    v = struct.unpack_from('<Q', d, p)[0]
    if imgbase + STR_LO <= v < imgbase + STR_HI:
        t = v - imgbase
        absp.setdefault(t, []).append(p)
print('targets:', len(absp), ' total ptrs:', sum(len(v) for v in absp.values()))
locs = sorted(p for v in absp.values() for p in v)
print('ptr locations span: 0x%x .. 0x%x' % (min(locs), max(locs)))
from collections import Counter
print(Counter(which(p) for p in locs))

# --- LEA 引用
print('\n===== RIP-relative LEA 引用 =====')
text = [s for s in secs if s[0] == '.text'][0]
_, tva, tvsz, traw, trsz = text
lea = {}
for p in range(traw, traw + trsz - 7):
    if d[p] in (0x48, 0x4C) and d[p+1] == 0x8D and (d[p+2] & 0xC7) == 0x05:
        disp = struct.unpack_from('<i', d, p+3)[0]
        tgt = off2rva(p) + 7 + disp
        if STR_LO <= tgt < STR_HI:
            lea.setdefault(tgt, []).append(off2rva(p))
print('LEA targets:', len(lea))
for t in sorted(lea):
    print('  rva=0x%06x x%d  %r' % (t, len(lea[t]), texts.get(t, '?')[:70]))

json.dump({'abs': {hex(k): [hex(x) for x in v] for k, v in absp.items()},
           'lea': {hex(k): [hex(x) for x in v] for k, v in lea.items()}},
          open(r'D:\Desktop\软件汉化\out\refs.json', 'w'), indent=1)
