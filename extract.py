"""统一提取 .rdata 中的 ANSI(UTF-8) 与 UTF-16LE 字符串，并定位全部引用。"""
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

rdata = [s for s in secs if s[0] == '.rdata'][0]
_, rva0, vsz0, raw0, rsz0 = rdata
LOF, HIF = raw0, raw0 + rsz0

def printable_w(ch):
    return (0x20 <= ch <= 0x7E) or ch in (9, 10, 13) or (0xA0 <= ch <= 0x2FFF) or (0x4E00 <= ch <= 0x9FFF) or ch in (0x2018,0x2019,0x201C,0x201D,0x2026,0x00A9)

# ---------- UTF-16LE（拉丁：奇数位必须为 0x00）----------
wide = {}
cons = bytearray(len(d))
wpat = re.compile(rb'(?:[\x20-\x7e\xa0-\xff]\x00){3,}')
for m in wpat.finditer(d, LOF, HIF):
    st = m.start()
    s = m.group().decode('utf-16-le')
    wide[off2rva(st)] = s
    for x in range(st, m.end()):
        cons[x] = 1

# ---------- ANSI ----------
ansi = {}
i = LOF
while i < HIF:
    if cons[i]:
        i += 1
        continue
    j = i
    while j < HIF and d[j] != 0 and not cons[j]:
        j += 1
    if 2 <= j - i <= 4000:
        b = d[i:j]
        if all(32 <= c < 127 or c in (9, 10, 13) for c in b) and any(65 <= c <= 90 or 97 <= c <= 122 for c in b):
            ansi[off2rva(i)] = b.decode('ascii')
    i = j + 1

print('wide strings:', len(wide), ' ansi strings:', len(ansi))
json.dump({'wide': {hex(k): v for k, v in wide.items()}, 'ansi': {hex(k): v for k, v in ansi.items()}},
          open(r'D:\Desktop\软件汉化\out\strings.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- 引用 ----------
pdrva, pdsize = struct.unpack_from('<II', d, opt + 112 + 3 * 8)

def r2o(rva): return rva2off(rva)
po = r2o(pdrva)
funcs = []
for i in range(pdsize // 12):
    b, en, u = struct.unpack_from('<III', d, po + i * 12)
    if b == 0 or en <= b:
        continue
    funcs.append((b, en))
funcs.sort()
md = Cs(CS_ARCH_X86, CS_MODE_64); md.detail = True
lea = {}
for b, en in funcs:
    o = rva2off(b)
    if o is None:
        continue
    for insn in md.disasm(d[o:o + (en - b)], b):
        if insn.address >= en:
            break
        for op in insn.operands:
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
                tgt = insn.address + insn.size + op.mem.disp
                if 0x42000 <= tgt < 0x52000:
                    lea.setdefault(tgt, []).append((insn.address, insn.size, op.mem.disp))
# 补充：函数表未覆盖的 LEA（人工校验后仅取 target 命中已知字符串者）
md1 = Cs(CS_ARCH_X86, CS_MODE_64); md1.detail = True
allstr = set(wide) | set(ansi)
extra = {}
for p in range(rva2off(0x1000), rva2off(0x1000) + [s for s in secs if s[0] == '.text'][0][4]):
    if not (d[p] == 0x8D or (0x40 <= d[p] <= 0x4F and p + 1 < len(d) and d[p+1] == 0x8D)):
        continue
    rv = off2rva(p)
    try:
        ins = next(md1.disasm(d[p:p+16], rv))
    except StopIteration:
        continue
    if ins.mnemonic != 'lea':
        continue
    for op in ins.operands:
        if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
            tgt = ins.address + ins.size + op.mem.disp
            if tgt in allstr:
                extra.setdefault(tgt, []).append((rv, ins.size, op.mem.disp))

absptr = {}
for p in range(0, len(d) - 8):
    v = struct.unpack_from('<Q', d, p)[0]
    if imgbase <= v < imgbase + szimage and 0x42000 <= (v - imgbase) < 0x52000:
        absptr.setdefault(v - imgbase, []).append(p)

out = {}
for r in allstr:
    a = absptr.get(r, [])
    l = lea.get(r, [])
    x = extra.get(r, [])
    out[r] = {'text': wide.get(r, ansi.get(r)), 'enc': 'utf-16' if r in wide else 'ansi',
              'abs': a, 'lea': l, 'lea_extra': x}
json.dump(out, open(r'D:\Desktop\软件汉化\out\refs_final.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('referenced strings:', len(out), ' with abs', sum(1 for v in out.values() if v['abs']),
      ' with lea', sum(1 for v in out.values() if v['lea']))
print('\nwide 中有引用的:')
for r, v in sorted(out.items()):
    if v['enc'] == 'utf-16':
        print('  0x%06x abs=%d lea=%d extra=%d %r' % (r, len(v['abs']), len(v['lea']), len(v['lea_extra']), v['text']))
