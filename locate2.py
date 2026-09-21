"""用 .pdata 函数表做精确反汇编，收集 .rdata 字符串的全部 RIP-LEA 引用。"""
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
# pdata dir = DataDirectory[3]
pdrva, pdsize = struct.unpack_from('<II', d, opt + 112 + 3 * 8)
print('pdata rva=0x%x size=0x%x' % (pdrva, pdsize))

def off2rva(off):
    for nm, va, vsz, raw, rsz in secs:
        if raw <= off < raw + rsz:
            return va + (off - raw)
def rva2off(rva):
    for nm, va, vsz, raw, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)

LO, HI = 0x42000, 0x52000
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

po = rva2off(pdrva)
funcs = []
for i in range(pdsize // 12):
    b, en, u = struct.unpack_from('<III', d, po + i * 12)
    if b == 0 or en <= b:
        continue
    funcs.append((b, en))
funcs.sort()
print('functions from .pdata:', len(funcs))

md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True
refs = {}
bad = 0
for b, en in funcs:
    o = rva2off(b)
    if o is None:
        continue
    code = d[o:o + (en - b)]
    for insn in md.disasm(code, b):
        if insn.address >= en:
            break
        for op in insn.operands:
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
                tgt = insn.address + insn.size + op.mem.disp
                if LO <= tgt < HI:
                    refs.setdefault(tgt, []).append((insn.address, insn.size, op.mem.disp))
print('RIP-LEA targets into .rdata:', len(refs), 'total refs', sum(len(v) for v in refs.values()))

# 绝对指针
absptr = {}
for p in range(0, len(d) - 8):
    v = struct.unpack_from('<Q', d, p)[0]
    if imgbase <= v < imgbase + szimage and LO <= (v - imgbase) < HI:
        absptr.setdefault(v - imgbase, []).append(p)

out = {}
for r in sorted(strs):
    a = absptr.get(r, [])
    l = refs.get(r, [])
    if a or l:
        out[str(r)] = {'text': strs[r].decode('utf-8', 'replace'), 'abs': a,
                       'lea': [list(x) for x in l]}
json.dump(out, open(r'D:\Desktop\软件汉化\out\locate.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('referenced strings:', len(out))
print('abs-only:', sum(1 for v in out.values() if v['abs'] and not v['lea']))
print('lea-only:', sum(1 for v in out.values() if not v['abs'] and v['lea']))
print('both:', sum(1 for v in out.values() if v['abs'] and v['lea']))
# UI 区间
ui = {r: v for r, v in out.items() if 0x431c0 <= int(r) < 0x44a00}
print('\nUI 区间(0x431c0-0x44a00) 有引用字符串:', len(ui))
print('  abs-only', sum(1 for v in ui.values() if v['abs'] and not v['lea']),
      ' lea-only', sum(1 for v in ui.values() if not v['abs'] and v['lea']),
      ' both', sum(1 for v in ui.values() if v['abs'] and v['lea']))
# 字符串池内无引用者
ui_all = [r for r in strs if 0x431c0 <= r < 0x44a00]
noref = [r for r in ui_all if r not in out]
print('  UI 区间无任何引用:', len(noref))
for r in noref:
    try:
        print('    0x%06x %r' % (r, strs[r].decode('utf-8')))
    except Exception:
        print('    0x%06x %r' % (r, strs[r]))
