import struct, json, re
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

# --- 全部 NUL 结尾字符串
rdata = [s for s in secs if s[0] == '.rdata'][0]
_, rva0, vsz0, raw0, rsz0 = rdata
strs = {}   # rva -> bytes
i = raw0
while i < raw0 + rsz0:
    j = i
    while j < raw0 + rsz0 and d[j] != 0:
        j += 1
    if 2 <= j - i <= 4000:
        strs[off2rva(i)] = d[i:j]
    i = j + 1

# --- 引用（capstone 线性 + 逐点候选校验）
text = [s for s in secs if s[0] == '.text'][0]
_, tva, tvsz, traw, trsz = text
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True
sweep_insns = []
code = d[traw:traw + trsz]
for insn in md.disasm(code, tva):
    sweep_insns.append((insn.address, insn.size))
    for op in insn.operands:
        if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
            tgt = insn.address + insn.size + op.mem.disp
            if 0x42000 <= tgt < 0x52000:
                pass

# 逐点候选：任何 8D modrm(mod=00,rm=101)
lea_cand = {}   # target -> [(insn_rva, file_off, disp_off_file)]
for p in range(traw, traw + trsz - 7):
    # 允许 1 个 REX 前缀
    for pre in (0, 1):
        q = p + pre
        if q + 6 > traw + trsz:
            continue
        if d[q] != 0x8D:
            continue
        modrm = d[q + 1]
        if (modrm & 0xC7) != 0x05:
            continue
        if pre == 1 and d[p] not in (0x40,0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,0x49,0x4A,0x4B,0x4C,0x4D,0x4E,0x4F):
            continue
        disp = struct.unpack_from('<i', d, q + 2)[0]
        instr_end_rva = off2rva(q) + 6
        tgt = instr_end_rva + disp
        if 0x42000 <= tgt < 0x52000:
            lea_cand.setdefault(tgt, []).append((off2rva(p) - pre, p, q + 2))
        break

# 绝对指针
absptr = {}
for p in range(0, len(d) - 8):
    v = struct.unpack_from('<Q', d, p)[0]
    if imgbase <= v < imgbase + szimage and 0x42000 <= (v - imgbase) < 0x52000:
        absptr.setdefault(v - imgbase, []).append(p)

# --- 输出：仅 UI 相关区域（rva 0x431c0 .. 0x44a00）
LO, HI = 0x431c0, 0x44a00
rows = []
for r in sorted(strs):
    if not (LO <= r < HI):
        continue
    b = strs[r]
    try:
        t = b.decode('utf-8')
    except Exception:
        t = b.decode('latin1')
    if not re.search(r'[A-Za-z]', t):
        continue
    rows.append(dict(rva=r, r=r, t=t, n=len(b),
                     absptr=[hex(x) for x in absptr.get(r, [])],
                     lea=[hex(x[0]) for x in lea_cand.get(r, [])]))
print('UI 候选字符串: %d' % len(rows))
only_lea = [x for x in rows if x['lea'] and not x['absptr']]
only_abs = [x for x in rows if x['absptr'] and not x['lea']]
both = [x for x in rows if x['absptr'] and x['lea']]
none = [x for x in rows if not x['absptr'] and not x['lea']]
print('  仅绝对指针: %d   仅LEA: %d   两者: %d   无引用: %d' % (len(only_abs), len(only_lea), len(both), len(none)))
json.dump(rows, open(r'D:\Desktop\软件汉化\out\ui_rows.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n--- 仅 LEA 引用（需就地改或补 disp）---')
for x in only_lea:
    print('  0x%06x len=%-3d %r  lea=%s' % (x['rva'], x['n'], x['t'][:60], x['lea']))
print('\n--- 无任何引用 ---')
for x in none[:40]:
    print('  0x%06x len=%-3d %r' % (x['rva'], x['n'], x['t'][:60]))
