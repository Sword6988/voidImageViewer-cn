"""定位 .rdata 字符串的全部引用：绝对指针 / RIP-LEA / 32 位 RVA。"""
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

def off2rva(off):
    for nm, va, vsz, raw, rsz in secs:
        if raw <= off < raw + rsz:
            return va + (off - raw)
def rva2off(rva):
    for nm, va, vsz, raw, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)

LO, HI = 0x42000, 0x52000

# ---- strings
rdata = [s for s in secs if s[0] == '.rdata'][0]
_, rva0, vsz0, raw0, rsz0 = rdata
strs = {}
i = raw0
while i < raw0 + rsz0:
    j = i
    while j < raw0 + rsz0 and d[j] != 0:
        j += 1
    if 2 <= j - i <= 4000:
        strs[off2rva(i)] = d[i:j]
    i = j + 1
print('strings in .rdata:', len(strs))

# ---- capstone linear sweep for RIP refs
text = [s for s in secs if s[0] == '.text'][0]
_, tva, tvsz, traw, trsz = text
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True
rip_sweep = {}
covered = set()
for insn in md.disasm(d[traw:traw + trsz], tva):
    for x in range(insn.address, insn.address + insn.size):
        covered.add(x)
    for op in insn.operands:
        if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
            tgt = insn.address + insn.size + op.mem.disp
            if LO <= tgt < HI:
                rip_sweep.setdefault(tgt, []).append((insn.address, insn.size, op.mem.disp))
print('sweep RIP targets:', len(rip_sweep))

# ---- candidate scan with per-address capstone validation
md1 = Cs(CS_ARCH_X86, CS_MODE_64); md1.detail = True
rip_cand = {}
extra = {}
for p in range(traw, traw + trsz - 8):
    if d[p] in (0x8D,) or (0x40 <= d[p] <= 0x4F and p + 1 < len(d) and d[p+1] == 0x8D):
        rva = off2rva(p)
        try:
            ins = next(md1.disasm(d[p:p+16], rva))
        except StopIteration:
            continue
        if ins.mnemonic != 'lea':
            continue
        for op in ins.operands:
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
                tgt = ins.address + ins.size + op.mem.disp
                if LO <= tgt < HI:
                    rip_cand.setdefault(tgt, []).append((rva, ins.size, op.mem.disp))
                    if rva not in covered:
                        extra.setdefault(tgt, []).append(rva)
print('candidate RIP targets:', len(rip_cand), ' sweep-missed extra refs:', sum(len(v) for v in extra.values()))
for t in sorted(extra):
    print('  extra tgt=0x%06x refs=%s' % (t, [hex(x) for x in extra[t]]))

# ---- absolute pointers
absptr = {}
for p in range(0, len(d) - 8):
    v = struct.unpack_from('<Q', d, p)[0]
    if imgbase <= v < imgbase + szimage and LO <= (v - imgbase) < HI:
        absptr.setdefault(v - imgbase, []).append(p)
print('abs ptr refs:', len(absptr), 'total', sum(len(v) for v in absptr.values()))

# ---- 32-bit RVA refs
r32 = {}
for p in range(0, len(d) - 4):
    v = struct.unpack_from('<I', d, p)[0]
    if LO <= v < HI:
        r32.setdefault(v, []).append(p)
print('32-bit RVA-looking refs (may be false positives):', len(r32))

out = {}
for r in strs:
    a = absptr.get(r, [])
    l = rip_cand.get(r, [])
    w = r32.get(r, [])
    if a or l or w:
        out[str(r)] = {'text': strs[r].decode('utf-8', 'replace'),
                       'abs': a,
                       'lea': [[x[0], x[1], x[2]] for x in l],
                       'lea_sweep': [[x[0], x[1], x[2]] for x in rip_sweep.get(r, [])],
                       'r32': w}
json.dump(out, open(r'D:\Desktop\软件汉化\out\locate.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nreferenced strings:', len(out))
n_lea_only_by_sweep = sum(1 for v in out.values() if v['lea_sweep'] and not v['abs'])
print('lea_sweep-only strings:', n_lea_only_by_sweep)
