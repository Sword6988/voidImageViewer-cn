# -*- coding: utf-8 -*-
"""Void Image Viewer 汉化构建器
   Stage A: 只重建 .rsrc（验证资源重建安全）
   Stage B: 完整汉化（新增 .cnstr 节 + 指针/LEA 重定位 + 资源重建）
"""
import struct, json, os, sys, hashlib

sys.path.insert(0, r'C:\Users\Shibeng\.workbuddy\skills\win32-exe-localizer\scripts')
from pe_res_engine import PE, load_resources, parse_dialog, enc_dialog, build_rsrc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translations as T

SRC = r'C:\Program Files\voidImageViewer\voidImageViewer.exe'
OUTDIR = r'D:\Desktop\软件汉化\out'
os.makedirs(OUTDIR, exist_ok=True)

# ------------------------------------------------ 载入
PEIMG = PE(SRC)
D = PEIMG.data
SECS = PEIMG.secs                       # [name, va, vsz, raw, rsz, hdr_off]
IMGBASE = struct.unpack_from('<Q', D, PEIMG.opt + 24)[0]
OPTSIZE = PEIMG.optsize
SECALIGN = struct.unpack_from('<I', D, PEIMG.opt + 32)[0]
FILEALIGN = struct.unpack_from('<I', D, PEIMG.opt + 36)[0]
NEWSEC_RVA = 0x60000

def off2rva(o):
    for n, va, vsz, raw, rsz, ho in SECS:
        if raw <= o < raw + rsz:
            return va + (o - raw)

def rva2off(r):
    for n, va, vsz, raw, rsz, ho in SECS:
        if va <= r <= va + max(vsz, rsz):
            return raw + (r - va)

def align(v, a):
    return (v + a - 1) // a * a

# ------------------------------------------------ 字符串 / 引用（复用 extract.py 的结果）
refs = json.load(open(os.path.join(OUTDIR, 'refs_final.json'), encoding='utf-8'))
strs = json.load(open(os.path.join(OUTDIR, 'strings.json'), encoding='utf-8'))
TR = T.merged()

# 校验：词典中每条 EN 是否真实存在于映像
missing = [en for en in TR if en not in strs['ansi'].values() and en not in strs['wide'].values()
           and en not in [x[1] for x in T.EXTRA_BY_RVA]]
print('翻译表条目 %d，未在映像中匹配到原文的条目: %d' % (len(TR), len(missing)))
for m in missing:
    print('   !! 未匹配:', repr(m))

# 建立 rva -> en 映射（只取需要翻译的）
targets = {}     # rva -> (en, zh, enc)
for enc_key, enc_name in (('ansi', 'ansi'), ('wide', 'utf-16')):
    for r, s in strs[enc_key].items():
        if s in TR and s not in [x[1] for x in T.EXTRA_BY_RVA]:
            targets[int(r, 0)] = (s, TR[s][0], enc_name)
for rva, en, zh in T.EXTRA_BY_RVA:
    targets[rva] = (en, zh, 'ansi')
print('待重定位字符串: %d' % len(targets))

# ------------------------------------------------ 去重 LEA 引用
def dedupe_lea(lst):
    s = sorted(set(tuple(x) for x in lst))
    out = []
    for a, size, disp in s:
        skip = False
        for a2, size2, disp2 in s:
            if a2 == a - 1:
                o = rva2off(a - 1)
                if o is not None and 0x40 <= D[o] <= 0x4F and size2 == size + 1:
                    skip = True
                    break
        if not skip:
            out.append((a, size, disp))
    return out

# ------------------------------------------------ 构造新字符串节
ORIG_BYTES = bytes(D)          # 未打补丁的原始映像（用于校验/统计）
blob = bytearray()
newoff = {}
inplace = []
noref = []
skipped = []
for rva in sorted(targets):
    en, zh, enc = targets[rva]
    o = rva2off(rva)
    # 原始字节长度（含结尾 NUL）
    if enc == 'utf-16':
        j = o
        while struct.unpack_from('<H', D, j)[0] != 0:
            j += 2
        origlen = (j + 2) - o
        newbytes = zh.encode('utf-16-le') + b'\0\0'
    else:
        j = o
        while D[j] != 0:
            j += 1
        origlen = (j + 1) - o
        newbytes = zh.encode('utf-8') + b'\0'

    info = refs.get(str(rva))
    has_ref = bool(info and (info['abs'] or info['lea'] or info['lea_extra']))
    if not has_ref:
        # 无任何引用（死字符串/调试串）-> 就地等长替换
        noref.append((rva, en))
        if len(newbytes) <= origlen:
            D[o:o + len(newbytes)] = newbytes
            for t in range(o + len(newbytes), o + origlen):
                D[t] = 0
            inplace.append((rva, en, zh))
        else:
            skipped.append((rva, en, zh, origlen, len(newbytes)))
        continue
    while len(blob) % 8:
        blob.append(0)
    newoff[rva] = NEWSEC_RVA + len(blob)
    blob += newbytes
print('重定位字符串 %d 条；无引用就地替换 %d 条；跳过 %d 条；新节大小 %d 字节'
      % (len(newoff), len(inplace), len(skipped), len(blob)))
for r, e, z, ol, nl in skipped:
    print('   [跳过·无引用且超长] rva=0x%06x %r (原 %d 字节 / 需 %d 字节)' % (r, e, ol, nl))

# ------------------------------------------------ 应用补丁
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_REG_RIP
_MD1 = Cs(CS_ARCH_X86, CS_MODE_64); _MD1.detail = True
_TEXTSEC = [s for s in SECS if s[0] == '.text'][0]


def refs_ondemand(rva):
    """扫描绝对指针 + RIP-LEA 引用（用于扫描器未收录的字符串）"""
    a = []
    for p in range(0, len(D) - 8):
        if struct.unpack_from('<Q', D, p)[0] == IMGBASE + rva:
            a.append(p)
    leas = []
    t0, t1 = _TEXTSEC[3], _TEXTSEC[3] + _TEXTSEC[4] - 8
    for q in range(t0, t1):
        if not (D[q] == 0x8D or (0x40 <= D[q] <= 0x4F and D[q + 1] == 0x8D)):
            continue
        try:
            ins = next(_MD1.disasm(bytes(D[q:q + 16]), off2rva(q)))
        except StopIteration:
            continue
        if ins.mnemonic != 'lea':
            continue
        for op in ins.operands:
            if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP:
                if ins.address + ins.size + op.mem.disp == rva:
                    leas.append((off2rva(q), ins.size, op.mem.disp))
    return a, dedupe_lea(leas)


patched_abs = 0
patched_lea = 0
lea_detail = []
for rva, newrva in newoff.items():
    info = refs.get(str(rva))
    if info is None:
        absl, leas = refs_ondemand(rva)
        print('  * 按需扫描 rva=0x%06x %r -> abs=%d lea=%d' % (rva, targets[rva][0], len(absl), len(leas)))
    else:
        absl = info['abs']
        leas = dedupe_lea(info['lea'] + info['lea_extra'])
    for p in absl:
        struct.pack_into('<Q', D, p, IMGBASE + newrva)
        patched_abs += 1
    for (addr, size, disp) in leas:
        o = rva2off(addr) + (size - 4)
        old = struct.unpack_from('<i', D, o)[0]
        if addr + size + old != rva:
            print('  !! LEA 校验失败 rva=0x%06x addr=0x%06x' % (rva, addr))
            continue
        struct.pack_into('<i', D, o, newrva - (addr + size))
        patched_lea += 1
        lea_detail.append((rva, addr, size))
print('已修补 绝对指针 %d 处, RIP-LEA 位移 %d 处' % (patched_abs, patched_lea))

# ================================================================
#  修复：程序内联的「逐字节拓宽」循环无法处理 UTF-8 多字节字符，
#  导致「选项 -> 控件」页的命令列表显示乱码。
#  做法：把 5 处内联循环改为调用代码洞 cave_strip_widen()：
#        先按 '&' 助记符规则剥离，再用程序自带的 MultiByteToWideChar(CP_UTF8)
#        包装函数 0x48B0 转换。返回时 rdx 指向译文末尾，由原终止指令收尾。
# ================================================================
MBTWC_RVA = 0x48b0          # void mbtwc(wchar_t* dest /*rcx*/, const char* src /*rdx*/)
LOOP_RVA = [0xcd80, 0x10150, 0x101c7, 0x13710, 0x13787]
LOOP_LEN = 45               # 循环主体长度（不含末尾写零指令）

while len(blob) % 16:
    blob.append(0)
CAVE_RVA = NEWSEC_RVA + len(blob)


def build_cave(cave_rva, mbtwc_rva):
    prog = [
        ('b', '4150'),            # push r8
        ('b', '4151'),            # push r9
        ('b', '4883EC38'),        # sub  rsp, 0x38
        ('b', '4889542420'),      # mov  [rsp+0x20], rdx      ; save dest
        ('b', '4887CA'),          # xchg rcx, rdx             ; rcx=dest, rdx=src
        ('call', mbtwc_rva),      # call mbtwc(CP_UTF8)
        ('b', '488B542420'),      # mov  rdx, [rsp+0x20]      ; rdx = dest (write ptr)
        ('b', '488BCA'),          # mov  rcx, rdx             ; rcx = dest (read ptr)
        ('lab', 'WLOOP'),
        ('b', '668B01'),          # mov  ax, [rcx]
        ('b', '6685C0'),          # test ax, ax
        ('jcc', 0x74, 'WDONE'),   # jz   WDONE
        ('b', '6683F826'),        # cmp  ax, 0x26             ; '&'
        ('jcc', 0x75, 'WCOPY'),   # jne  WCOPY
        ('b', '66394102'),        # cmp  [rcx+2], ax          ; "&&"
        ('jcc', 0x75, 'WSKIP'),   # jne  WSKIP
        ('b', '668902'),          # mov  [rdx], ax            ; '&&' -> '&'
        ('b', '4883C202'),        # add  rdx, 2
        ('b', '4883C104'),        # add  rcx, 4
        ('jmp', 'WLOOP'),
        ('lab', 'WCOPY'),
        ('b', '668902'),          # mov  [rdx], ax
        ('b', '4883C202'),        # add  rdx, 2
        ('b', '4883C102'),        # add  rcx, 2
        ('jmp', 'WLOOP'),
        ('lab', 'WSKIP'),
        ('b', '4883C102'),        # add  rcx, 2               ; 丢掉单 '&'
        ('jmp', 'WLOOP'),
        ('lab', 'WDONE'),
        ('b', '4883C438'),        # add  rsp, 0x38
        ('b', '4159'),            # pop  r9
        ('b', '4158'),            # pop  r8
        ('b', 'C3'),              # ret
    ]
    code = bytearray(); L = {}; fixes = []
    for it in prog:
        if it[0] == 'b':
            code.extend(bytes.fromhex(it[1]))
        elif it[0] == 'lab':
            L[it[1]] = len(code)
        elif it[0] == 'call':
            code.append(0xE8); fixes.append((len(code), 4, 'abs', it[1])); code.extend(b'\0' * 4)
        elif it[0] == 'jmp':
            code.append(0xEB); fixes.append((len(code), 1, 'rel', it[1])); code.append(0)
        elif it[0] == 'jcc':
            code.append(it[1]); fixes.append((len(code), 1, 'rel', it[2])); code.append(0)
    for off, size, kind, tgt in fixes:
        end = cave_rva + off + size
        val = (tgt - end) if kind == 'abs' else (cave_rva + L[tgt] - end)
        code[off:off + size] = struct.pack('<i' if size == 4 else '<b', val)
    return bytes(code)


cave = build_cave(CAVE_RVA, MBTWC_RVA)
print('代码洞 cave_strip_widen @rva=0x%06x (%d 字节)' % (CAVE_RVA, len(cave)))

for start in LOOP_RVA:
    o = rva2off(start)
    assert D[o] == 0x3C and D[o + 1] == 0x26, '循环起始字节不符 @0x%06x' % start
    assert D[o + LOOP_LEN] in (0x66, 0x48), '循环长度不符 @0x%06x' % start
    struct.pack_into('<i', D, o + 1, CAVE_RVA - (start + 5))
    D[o] = 0xE8
    for k in range(5, LOOP_LEN):
        D[o + k] = 0x90
for rva, addr, size in lea_detail:
    assert not (MBTWC_RVA <= addr < MBTWC_RVA + 0x2A), '转换函数被 LEA 补丁命中'
    assert not any(s <= addr < s + LOOP_LEN for s in LOOP_RVA), '循环区被 LEA 补丁命中'
print('已重定向 1:1 拓宽循环 %d 处 -> UTF-8 转换' % len(LOOP_RVA))

blob += cave

# ------------------------------------------------ 重建 .rsrc（对话框汉化）
res = load_resources(PEIMG)
dlg_hits = []
for r in res:
    if r.kind != 'DIALOG':
        continue
    dlg, consumed = parse_dialog(r.blob)

    def tr_title(f, where):
        if f[0] == 'str' and f[1] in TR:
            dlg_hits.append((r.name, where, f[1], TR[f[1]][0]))
            return ('str', TR[f[1]][0])
        return f

    dlg.title = tr_title(dlg.title, 'title')
    for it in dlg.items:
        it.title = tr_title(it.title, 'id=%s' % it.id)
    r.new_blob = enc_dialog(dlg)
print('对话框文本替换: %d 处' % len(dlg_hits))

rsrc_blob = build_rsrc(res, PEIMG.res_rva)
print('新 .rsrc 大小 %d (原 %d), 上限 %d' % (len(rsrc_blob), PEIMG.res_size, 0x60000 - 0x5a000))
assert len(rsrc_blob) <= 0x60000 - 0x5a000, '资源段超出可用虚拟空间'

# ------------------------------------------------ 重新布局文件
rsrc_sec = PEIMG.sec('.rsrc')
RSRC_OFF = rsrc_sec[3]
rsrc_raw_size = align(len(rsrc_blob), FILEALIGN)
cnstr_off = RSRC_OFF + rsrc_raw_size
cnstr_raw_size = align(len(blob), FILEALIGN)
overlay_off = cnstr_off + cnstr_raw_size

# overlay = 原 Authenticode 签名（原样搬到文件末尾）
orig_end_raw = max(s[3] + s[4] for s in SECS)
overlay = bytes(D[orig_end_raw:])
print('overlay(数字签名) %d 字节 -> 新偏移 0x%x' % (len(overlay), overlay_off))

newdata = bytearray(D[:RSRC_OFF])
newdata += rsrc_blob
newdata += b'\0' * (rsrc_raw_size - len(rsrc_blob))
cnstr_file_off = len(newdata)
assert cnstr_file_off == cnstr_off
newdata += blob
newdata += b'\0' * (cnstr_raw_size - len(blob))
newdata += overlay

# ---- 更新 .rsrc 节头
ho = rsrc_sec[5]
# 节头: Name[8] VirtualSize(4) VirtualAddress(4) SizeOfRawData(4) PointerToRawData(4) ...
struct.pack_into('<IIII', newdata, ho + 8, len(rsrc_blob), rsrc_sec[1], rsrc_raw_size, RSRC_OFF)

# ---- 追加新节头
nsec = len(SECS)
newho = PEIMG.sec_off + nsec * 40
assert newho + 40 <= struct.unpack_from('<I', D, PEIMG.opt + 60)[0], '节头空间不足'
name = b'.cnstr\0\0'
newdata[newho:newho + 8] = name
struct.pack_into('<IIII', newdata, newho + 8, len(blob), NEWSEC_RVA, cnstr_raw_size, cnstr_file_off)
struct.pack_into('<I', newdata, newho + 36, 0x60000020)   # CNT_CODE | MEM_EXECUTE | MEM_READ（含代码洞）
# NumberOfSections
struct.pack_into('<H', newdata, (struct.unpack_from('<I', D, 0x3C)[0]) + 6, nsec + 1)

# ---- DataDirectory[2] (.rsrc) Size；DataDirectory[4] (证书表) 偏移
struct.pack_into('<II', newdata, PEIMG.ddir + 16, PEIMG.res_rva, len(rsrc_blob))
if overlay:
    struct.pack_into('<II', newdata, PEIMG.ddir + 4 * 8, overlay_off, len(overlay))
else:
    struct.pack_into('<II', newdata, PEIMG.ddir + 4 * 8, 0, 0)

# ---- SizeOfImage
newsize = align(NEWSEC_RVA + len(blob), SECALIGN)
struct.pack_into('<I', newdata, PEIMG.opt + 56, newsize)

# ---- 校正 PE 校验和
ck_off = PEIMG.opt + 64
struct.pack_into('<I', newdata, ck_off, 0)
chk = 0
for i in range(0, len(newdata) - 1, 2):
    chk += struct.unpack_from('<H', newdata, i)[0]
    chk = (chk & 0xFFFF) + (chk >> 16)
if len(newdata) % 2:
    chk += newdata[-1]
    chk = (chk & 0xFFFF) + (chk >> 16)
chk = (chk & 0xFFFF) + (chk >> 16)
chk += len(newdata)
struct.pack_into('<I', newdata, ck_off, chk & 0xFFFFFFFF)

OUT = os.path.join(OUTDIR, 'voidImageViewer.cn.exe')
open(OUT, 'wb').write(bytes(newdata))
print('\n输出: %s  (%d 字节, 原 %d)' % (OUT, len(newdata), len(D)))
print('原 MD5:', hashlib.md5(ORIG_BYTES).hexdigest())
print('新 MD5:', hashlib.md5(bytes(newdata)).hexdigest())
json.dump({'patched_abs': patched_abs, 'patched_lea': patched_lea, 'inplace': inplace, 'skipped': skipped,
           'cave_rva': CAVE_RVA, 'cave_len': len(cave), 'loops_fixed': LOOP_RVA,
           'strings': {hex(k): {'en': targets[k][0], 'zh': targets[k][1],
                                'newrva': newoff.get(k), 'enc': targets[k][2]} for k in targets},
           'dlg_hits': dlg_hits},
          open(os.path.join(OUTDIR, 'build_report.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('NewSectionRVA=0x%x SizeOfImage=0x%x' % (NEWSEC_RVA, newsize))
