import struct, json
from capstone import *
from capstone.x86 import X86_OP_MEM, X86_REG_RIP

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
sizehdr = struct.unpack_from('<I', d, opt + 60)[0]
filealign = struct.unpack_from('<I', d, opt + 36)[0]
secalign = struct.unpack_from('<I', d, opt + 32)[0]
print('SizeOfImage', hex(szimage), 'SizeOfHeaders', hex(sizehdr), 'FileAlign', hex(filealign), 'SecAlign', hex(secalign))
print('numsec', nsec, 'sechdr_end', hex(so + nsec * 40))

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

# ---------- 1. 精确 LEA 引用（capstone 线性扫描 .text） ----------
text = [s for s in secs if s[0] == '.text'][0]
_, tva, tvsz, traw, trsz = text
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True
lea_refs = {}      # target_rva -> [insn_rva]
rip_ops = {}       # target_rva -> list of (insn_rva, istart_off, isize, disp_off)
code = d[traw:traw + trsz]
base_rva = tva
for insn in md.disasm(code, base_rva):
    for op in insn.operands:
        if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
            tgt = insn.address + insn.size + op.mem.disp
            if 0x42000 <= tgt < 0x52000:
                rip_ops.setdefault(tgt, []).append(
                    (insn.address, traw + (insn.address - base_rva), insn.size, op.mem.disp))
print('\ncapstone RIP-refs into .rdata:', len(rip_ops), 'total', sum(len(v) for v in rip_ops.values()))

# ---------- 2. 绝对指针 ----------
absptr = {}
for p in range(0, len(d) - 8):
    v = struct.unpack_from('<Q', d, p)[0]
    if imgbase <= v < imgbase + szimage:
        t = v - imgbase
        if 0x42000 <= t < 0x52000:
            absptr.setdefault(t, []).append(p)
print('absptrs into .rdata:', len(absptr), 'total', sum(len(v) for v in absptr.values()))

# ---------- 3. .data 表结构 ----------
locs = sorted(p for v in absptr.values() for p in v)
print('absptr range 0x%x..0x%x' % (min(locs), max(locs)))
tbl = sorted(p for p in locs if p >= 0x4f000)
print('table region count', len(tbl), 'first', hex(tbl[0]), 'last', hex(tbl[-1]))
print('\n=== .data 表（偏移, 指向字符串）===')
for p in tbl[:6] + tbl[-6:]:
    off = rva2off(struct.unpack_from('<Q', d, p)[0] - imgbase)
    end = d.index(b'\0', off)
    print('  %06x -> %r' % (p, d[off:end].decode('utf-8', 'replace')))

json.dump({'rip': {hex(k): [[hex(a), hex(b), c, e] for a, b, c, e in v] for k, v in rip_ops.items()},
           'abs': {hex(k): [hex(x) for x in v] for k, v in absptr.items()}},
          open(r'D:\Desktop\软件汉化\out\refs2.json', 'w'))

# ---------- 4. overlay ----------
endraw = max(s[3] + s[4] for s in secs)
print('\nmax section raw end 0x%x, file size 0x%x' % (endraw, len(d)))
print('overlay bytes:', len(d) - endraw)
print('overlay head:', d[endraw:endraw + 32].hex())
