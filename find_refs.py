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

# 目标：字符串池 RVA 范围
TARGET_LO, TARGET_HI = 0x43280, 0x44a00   # &About .. Slideshow Play/Pause 附近

text = [s for s in secs if s[0] == '.text'][0]
_, tva, tvsz, traw, trsz = text
hits = {}
for p in range(traw, traw + trsz - 8):
    # 检查是否 LEA 形式: 48/4C 8D modrm(mod=00,rm=101)
    if d[p] in (0x48, 0x4C) and d[p+1] == 0x8D and (d[p+2] & 0xC7) == 0x05:
        disp = struct.unpack_from('<i', d, p+3)[0]
        instr_end_rva = off2rva(p) + 7
        tgt = instr_end_rva + disp
        if TARGET_LO <= tgt < TARGET_HI:
            hits.setdefault(tgt, []).append(off2rva(p))
print('LEA 命中数:', len(hits))
found_rvas = sorted(hits)
print('其中字符串池内被 LEA 引用的 RVA 个数:', len(found_rvas))
for r in found_rvas[:40]:
    off = rva2off(r)
    end = d.index(b'\0', off)
    print('  rva=0x%06x  refs=%d  %r' % (r, len(hits[r]), d[off:end].decode('utf-8', 'replace')))

# 另外：搜索 8字节指针表（.rdata/.data 中直接存放 RVA 值已不可能，x64 用绝对地址）
# 检查是否存在绝对地址表：image base
imgbase = struct.unpack_from('<Q', d, opt + 24)[0]
print('\nImageBase =', hex(imgbase))
abs_hits = {}
for p in range(0, len(d) - 8, 8):
    v = struct.unpack_from('<Q', d, p)[0]
    if imgbase + TARGET_LO <= v < imgbase + TARGET_HI:
        abs_hits.setdefault(v - imgbase, []).append(hex(p))
print('绝对地址表命中:', len(abs_hits))
for r in sorted(abs_hits)[:20]:
    off = rva2off(r)
    end = d.index(b'\0', off)
    print('  rva=0x%06x at %s -> %r' % (r, abs_hits[r][:3], d[off:end].decode('utf-8', 'replace')))
