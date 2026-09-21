# -*- coding: utf-8 -*-
"""Void Image Viewer 汉化包 —— 版本自适应重建器
================================================================
把「已安装的原版 voidImageViewer.exe」重新生成为汉化版。

与旧构建器（build.py）的区别：**不再依赖硬编码 RVA**。
所有定位项都改为「内容签名」：

  1) 待翻译字符串   —— 按原文文本内容在 .rdata/.data 中检索
  2) 字符串引用     —— 一次全映像扫描：绝对指针(8字节) + RIP相对 LEA
  3) 1:1 拓宽循环   —— 45 字节代码模板（5 处完全相同，跨版本稳定）
  4) UTF-8 转换函数 —— 33 字节代码模板（含 mov ecx, 0FDE9h 即 CP_UTF8）
  5) 新节 RVA       —— 由最后一段节区的 VA+VSIZE 对齐算出

因此同作者的版本升级后，只要上述「文本 + 代码形状」未被改写，
本脚本无需修改即可重新生成汉化版。

用法：
    python rebuild_cn.py                       # 生成到 cn_out/（不动安装目录）
    python rebuild_cn.py --deploy              # 备份后覆盖安装目录中的 exe
    python rebuild_cn.py --target <exe路径>     # 指定其它目标
    python rebuild_cn.py --verify              # 生成后启动程序并读取菜单自检
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pe_res_engine import PE, load_resources, parse_dialog, enc_dialog, build_rsrc  # noqa: E402
import translations as T  # noqa: E402

DEFAULT_TARGET = r"C:\Program Files\voidImageViewer\voidImageViewer.exe"
SECNAME = b".cnstr\0\0"

# ---------------------------------------------------------------- 代码模板
# 5 处「逐字节 1:1 拓宽」内联循环，45 字节，实测 5 处逐字节相同
SIG_WIDEN = bytes.fromhex(
    "3c267514384101751a66c70226004883c2024883c102eb0f"
    "0fb6c04883c202668942fe4883c1018a0184c075d3")
LOOP_LEN = 45

# MultiByteToWideChar 包装函数头（33 字节，止于 call 的操作码 FF15）
SIG_MBTWC = bytes.fromhex(
    "4883ec384c8bc2c74424280004000048894c2420b9e9fd00004183c9ff33d2ff15")
# 退化锚点：mov ecx, 0FDE9h (CP_UTF8)，其后 20 字节内必须出现 call qword [rip+x]
ANCHOR_CP_UTF8 = bytes.fromhex("b9e9fd0000")

# 拓宽循环尾部必须紧跟「写宽字符 0 结尾」指令
TAIL_OK = (0x66, 0x48)


# ================================================================ 工具
def align(v, a):
    return (v + a - 1) // a * a


def eprint(*a):
    print(*a, file=sys.stderr)


# ================================================================ 1. 字符串扫描
def _is_ascii_print(b):
    """ANSI 字符串允许的字节：可打印 ASCII + \\t \\n \\r。
    刻意不把 >=0x80 视为可打印——否则串首会被高位字节污染（例如 0x83 紧邻 ':Pos ...'）。"""
    return 0x20 <= b <= 0x7E or b in (0x09, 0x0A, 0x0D)


def scan_strings(img):
    """扫描 .rdata/.data，返回 {'ansi': {rva: text}, 'wide': {rva: text}}"""
    data = img.data
    ansi, wide = {}, {}
    for name, va, vsz, raw, rsz, _ho in img.secs:
        if name not in (".rdata", ".data", ".rodata"):
            continue
        blob = bytes(data[raw:raw + rsz])
        n = len(blob)

        # ---- ANSI ----
        i = 0
        while i < n:
            if _is_ascii_print(blob[i]):
                j = i
                while j < n and _is_ascii_print(blob[j]):
                    j += 1
                if j < n and blob[j] == 0 and j - i >= 2:
                    txt = blob[i:j].decode("ascii")
                    if txt.strip():
                        ansi[va + i] = txt
                i = j + 1
            else:
                i += 1

        # ---- UTF-16LE ----
        i = 0
        while i + 1 < n:
            lo, hi = blob[i], blob[i + 1]
            if hi == 0 and _is_ascii_print(lo):
                j = i
                while j + 1 < n and blob[j + 1] == 0 and _is_ascii_print(blob[j]):
                    j += 2
                if j + 1 < n and blob[j] == 0 and blob[j + 1] == 0 and (j - i) >= 4:
                    txt = blob[i:j].decode("utf-16-le")
                    if txt.strip():
                        wide[va + i] = txt
                i = j + 2
            else:
                i += 1
    return {"ansi": ansi, "wide": wide}


# ================================================================ 2. 引用索引
def _r2o_map(img):
    m = []
    for _n, va, vsz, raw, rsz, _ho in img.secs:
        m.append((va, max(vsz, rsz), raw))
    return m


def rva2off(img, r):
    for va, sz, raw in _r2o_map(img):
        if va <= r < va + sz:
            return raw + (r - va)
    return None


def off2rva(img, o):
    for _n, va, _vsz, raw, rsz, _ho in img.secs:
        if raw <= o < raw + rsz:
            return va + (o - raw)
    return None


def build_abs_index(img, targets):
    """全映像扫描 8 字节绝对指针，值落在 targets 集合内则记录（文件偏移）。"""
    data = img.data
    base = struct.unpack_from("<Q", data, img.opt + 24)[0]
    uns = struct.Struct("<Q").unpack_from
    out = {}
    for o in range(0, len(data) - 8):
        v = uns(data, o)[0]
        if v >= base:
            r = v - base
            if r in targets:
                out.setdefault(r, []).append(o)
    return out


def build_lea_index(img, targets):
    """手工解码 .text 中的 `lea reg,[rip+disp32]`，记录指向 targets 的位置。

    注意：同一条指令会被匹配两次——一次落在可选的 REX 前缀(0x40-0x4F)上、
    一次落在 0x8D 上。两者算出的「位移字节文件偏移」相同，这里按该偏移去重。
    """
    sec = [s for s in img.secs if s[0] == ".text"][0]
    _n, _va, _vsz, raw, rsz, _ho = sec
    data = img.data
    sites = {}
    for q in range(raw, raw + rsz - 7):
        b = data[q]
        if b == 0x8D:
            rex, p = 0, q
        elif 0x40 <= b <= 0x4F and data[q + 1] == 0x8D:
            rex, p = 1, q + 1
        else:
            continue
        modrm = data[p + 1]
        if (modrm >> 6) != 0 or (modrm & 7) != 5:      # 必须 mod=00, rm=101 (RIP)
            continue
        size = rex + 6                                  # REX? + 8D + modrm + disp32
        addr = off2rva(img, q)
        if addr is None:
            continue
        disp = struct.unpack_from("<i", data, p + 2)[0]
        tgt = addr + size + disp
        if tgt not in targets:
            continue
        o = q + (size - 4)                              # 位移字段的文件偏移
        if addr + size + struct.unpack_from("<i", data, o)[0] != tgt:
            continue                                    # 自校验
        sites.setdefault(o, (tgt, addr, size, disp))
    out = {}
    for o in sorted(sites):
        tgt, addr, size, disp = sites[o]
        out.setdefault(tgt, []).append((addr, size, disp))
    return out


# ================================================================ 3. 代码模板定位
def find_all(img, sig, secname=".text"):
    sec = [s for s in img.secs if s[0] == secname][0]
    _n, _va, _vsz, raw, rsz, _ho = sec
    blob = bytes(img.data[raw:raw + rsz])
    hits, i = [], 0
    while True:
        j = blob.find(sig, i)
        if j < 0:
            break
        hits.append(off2rva(img, raw + j))
        i = j + 1
    return hits


def locate_mbtwc(img):
    """定位 MultiByteToWideChar(CP_UTF8) 包装函数。返回 RVA 或 None。"""
    hits = find_all(img, SIG_MBTWC)
    if len(hits) == 1:
        return hits[0], "完整模板"
    # 退化：锚点 + 邻近 call qword [rip+x]
    anch = find_all(img, ANCHOR_CP_UTF8)
    good = []
    for a in anch:
        o = rva2off(img, a)
        seg = bytes(img.data[o:o + 24])
        if b"\xff\x15" in seg:
            # 函数头应在前 16 字节内（sub rsp,imm / mov 系列）
            start = a
            for k in range(1, 24):
                so = o - k
                if so < 0:
                    break
                if img.data[so] == 0x48 and img.data[so + 1] == 0x83 and img.data[so + 2] == 0xEC:
                    start = off2rva(img, so)
                    break
            good.append(start)
    if len(good) == 1:
        return good[0], "锚点推断"
    if hits:
        return None, "模板命中 %d 处，歧义" % len(hits)
    return None, "未找到（命中 %d 处锚点）" % len(good)


# ================================================================ 4. 代码洞
def build_cave(cave_rva, mbtwc_rva):
    """生成 code cave：剥离 & 助记符 + 调 UTF-8 转换。
    入参 rcx=src(ANSI), rdx=dest(wchar)；返回时 rdx 指向译文末尾。"""
    prog = [
        ('b', '4150'),            # push r8
        ('b', '4151'),            # push r9
        ('b', '4883EC38'),        # sub  rsp, 0x38
        ('b', '4889542420'),      # mov  [rsp+0x20], rdx      ; 保存 dest
        ('b', '4887CA'),          # xchg rcx, rdx             ; rcx=dest, rdx=src
        ('call', mbtwc_rva),      # call mbtwc(CP_UTF8)
        ('b', '488B542420'),      # mov  rdx, [rsp+0x20]
        ('b', '488BCA'),          # mov  rcx, rdx
        ('lab', 'WLOOP'),
        ('b', '668B01'),          # mov  ax, [rcx]
        ('b', '6685C0'),          # test ax, ax
        ('jcc', 0x74, 'WDONE'),   # jz   WDONE
        ('b', '6683F826'),        # cmp  ax, 0x26
        ('jcc', 0x75, 'WCOPY'),   # jne  WCOPY
        ('b', '66394102'),        # cmp  [rcx+2], ax
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
        ('b', '4883C102'),        # add  rcx, 2               ; 丢弃单 '&'
        ('jmp', 'WLOOP'),
        ('lab', 'WDONE'),
        ('b', '4883C438'),        # add  rsp, 0x38
        ('b', '4159'),            # pop  r9
        ('b', '4158'),            # pop  r8
        ('b', 'C3'),              # ret
    ]
    code, L, fixes = bytearray(), {}, []
    for it in prog:
        if it[0] == 'b':
            code.extend(bytes.fromhex(it[1]))
        elif it[0] == 'lab':
            L[it[1]] = len(code)
        elif it[0] == 'call':
            code.append(0xE8)
            fixes.append((len(code), 4, 'abs', it[1]))
            code.extend(b'\0' * 4)
        elif it[0] == 'jmp':
            code.append(0xEB)
            fixes.append((len(code), 1, 'rel', it[1]))
            code.append(0)
        elif it[0] == 'jcc':
            code.append(it[1])
            fixes.append((len(code), 1, 'rel', it[2]))
            code.append(0)
    for off, size, kind, tgt in fixes:
        end = cave_rva + off + size
        val = (tgt - end) if kind == 'abs' else (cave_rva + L[tgt] - end)
        code[off:off + size] = struct.pack('<i' if size == 4 else '<b', val)
    return bytes(code)


# ================================================================ 5. 主流程
def build(target, out_path, report_path):
    img = PE(target)
    D = img.data
    SECS = img.secs
    IMGBASE = struct.unpack_from('<Q', D, img.opt + 24)[0]
    magic = struct.unpack_from('<H', D, img.opt)[0]
    DDIR = img.opt + (112 if magic == 0x20B else 96)
    SECALIGN = struct.unpack_from('<I', D, img.opt + 32)[0]
    FILEALIGN = struct.unpack_from('<I', D, img.opt + 36)[0]

    print("目标: %s" % target)
    print("  ImageBase=%#x  节区=%d  节对齐=%#x 文件对齐=%#x" % (IMGBASE, len(SECS), SECALIGN, FILEALIGN))

    sec_str = SECNAME.rstrip(b'\0').decode()
    if any(s[0].rstrip('\0') == sec_str for s in SECS):
        raise SystemExit("!! 目标已含 %s 节，疑似已经是汉化版。请先用安装包里的原版覆盖后再运行。" % sec_str)

    # ---- (1) 字符串 ----
    pool = scan_strings(img)
    print("  扫描到 ANSI 字符串 %d 条 / UTF-16 字符串 %d 条"
          % (len(pool['ansi']), len(pool['wide'])))

    TR = T.merged()
    for _rva, en, zh in T.EXTRA_BY_RVA:          # 旧表里的 RVA 不再使用，按文本并入
        TR[en] = (zh, "内部调试信息")

    # 内容 -> [rva] 反向索引
    bytext = {}
    for enc, d in (('ansi', pool['ansi']), ('wide', pool['wide'])):
        for rva, s in d.items():
            bytext.setdefault(s, []).append((rva, enc))

    targets, unmatched = {}, []
    for en, (zh, area) in TR.items():
        cands = bytext.get(en)
        if not cands:
            unmatched.append(en)
            continue
        for rva, enc in cands:
            targets[rva] = (en, zh, "utf-16" if enc == 'wide' else "ansi")
    print("  翻译表 %d 条 -> 命中映像中字符串 %d 处；未命中 %d 条"
          % (len(TR), len(targets), len(unmatched)))
    for m in unmatched:
        print("     [未命中] %r" % m)

    # ---- (2) 引用索引 ----
    tset = set(targets)
    abs_index = build_abs_index(img, tset)
    lea_index = build_lea_index(img, tset)
    print("  引用索引：绝对指针目标 %d 个 / LEA 目标 %d 个"
          % (len(abs_index), len(lea_index)))

    # ---- (3) 代码模板 ----
    loops = find_all(img, SIG_WIDEN)
    bad_tail = [r for r in loops if D[rva2off(img, r) + LOOP_LEN] not in TAIL_OK]
    loops = [r for r in loops if r not in bad_tail]
    mbtwc, how = locate_mbtwc(img)
    print("  代码模板：拓宽循环 %d 处 %s；UTF-8 转换函数 %s"
          % (len(loops), ("(剔除尾部异常 %d)" % len(bad_tail)) if bad_tail else "",
             ("%#x [%s]" % (mbtwc, how)) if mbtwc else "!! 未定位 " + how))
    if not loops:
        raise SystemExit("!! 未能定位拓宽循环，版本结构可能已变化，请人工检查 SIG_WIDEN。")
    if mbtwc is None:
        raise SystemExit("!! 未能定位 UTF-8 转换函数（%s），请人工检查 SIG_MBTWC。" % how)

    # ---- (4) 新节 ----
    last = max(SECS, key=lambda s: s[1] + s[2])
    newsec_rva = align(last[1] + align(last[2], SECALIGN), SECALIGN)
    print("  新节 .cnstr RVA = %#x" % newsec_rva)

    # ---- 构造新字符串 blob ----
    ORIG = bytes(D)
    blob = bytearray()
    newoff, inplace, skipped = {}, [], []
    for rva in sorted(targets):
        en, zh, enc = targets[rva]
        o = rva2off(img, rva)
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

        if not (abs_index.get(rva) or lea_index.get(rva)):
            if len(newbytes) <= origlen:        # 无引用 -> 就地等长替换
                D[o:o + len(newbytes)] = newbytes
                for t in range(o + len(newbytes), o + origlen):
                    D[t] = 0
                inplace.append((rva, en, zh))
            else:
                skipped.append((rva, en, zh, origlen, len(newbytes)))
            continue
        while len(blob) % 8:
            blob.append(0)
        newoff[rva] = newsec_rva + len(blob)
        blob += newbytes
    print("  重定位 %d 条 / 就地替换 %d 条 / 跳过 %d 条；新节数据 %d 字节"
          % (len(newoff), len(inplace), len(skipped), len(blob)))
    for r, e, z, ol, nl in skipped:
        print("     [跳过·无引用且超长] rva=%#x %r (原 %d / 需 %d)" % (r, e, ol, nl))

    # ---- 打补丁 ----
    p_abs = p_lea = 0
    lea_used = []
    for rva, newrva in newoff.items():
        for p in abs_index.get(rva, []):
            struct.pack_into('<Q', D, p, IMGBASE + newrva)
            p_abs += 1
        for (addr, size, disp) in lea_index.get(rva, []):
            o = rva2off(img, addr) + (size - 4)
            old = struct.unpack_from('<i', D, o)[0]
            if addr + size + old != rva:
                eprint("     !! LEA 校验失败 rva=%#x addr=%#x" % (rva, addr))
                continue
            struct.pack_into('<i', D, o, newrva - (addr + size))
            p_lea += 1
            lea_used.append((addr, size))
    print("  已修补 绝对指针 %d 处 / RIP-LEA %d 处" % (p_abs, p_lea))

    # ---- 代码洞 + 重定向 ----
    while len(blob) % 16:
        blob.append(0)
    cave_rva = newsec_rva + len(blob)
    cave = build_cave(cave_rva, mbtwc)
    for start in loops:
        o = rva2off(img, start)
        assert D[o] == 0x3C and D[o + 1] == 0x26, '循环起始字节不符 @%#x' % start
        struct.pack_into('<i', D, o + 1, cave_rva - (start + 5))
        D[o] = 0xE8
        for k in range(5, LOOP_LEN):
            D[o + k] = 0x90
    for addr, size in lea_used:
        assert not (mbtwc <= addr < mbtwc + 0x40), '转换函数被 LEA 补丁命中'
        assert not any(s <= addr < s + LOOP_LEN for s in loops), '循环区被 LEA 补丁命中'
    print("  代码洞 @%#x (%d 字节)；重定向拓宽循环 %d 处" % (cave_rva, len(cave), len(loops)))
    blob += cave

    # ---- 重建 .rsrc ----
    res = load_resources(img)
    dlg_hits = []
    for r in res:
        if r.kind != 'DIALOG':
            continue
        dlg, _consumed = parse_dialog(r.blob)

        def tr_title(f):
            if f[0] == 'str' and f[1] in TR:
                dlg_hits.append((r.name, f[1], TR[f[1]][0]))
                return ('str', TR[f[1]][0])
            return f

        dlg.title = tr_title(dlg.title)
        for it in dlg.items:
            it.title = tr_title(it.title)
        r.new_blob = enc_dialog(dlg)
    rsrc_blob = build_rsrc(res, img.res_rva)
    print("  对话框文本 %d 处；新 .rsrc %d 字节 (原 %d)"
          % (len(dlg_hits), len(rsrc_blob), img.res_size))

    # ---- 重新布局 ----
    rsec = [s for s in SECS if s[0] == '.rsrc'][0]
    RSRC_OFF = rsec[3]
    rsrc_raw = align(len(rsrc_blob), FILEALIGN)
    cnstr_off = RSRC_OFF + rsrc_raw
    cnstr_raw = align(len(blob), FILEALIGN)
    overlay_off = cnstr_off + cnstr_raw

    orig_end = max(s[3] + s[4] for s in SECS)
    overlay = bytes(D[orig_end:])
    print("  overlay(数字签名) %d 字节 -> %#x" % (len(overlay), overlay_off))

    nd = bytearray(D[:RSRC_OFF])
    nd += rsrc_blob
    nd += b'\0' * (rsrc_raw - len(rsrc_blob))
    assert len(nd) == cnstr_off
    nd += blob
    nd += b'\0' * (cnstr_raw - len(blob))
    nd += overlay

    struct.pack_into('<IIII', nd, rsec[5] + 8, len(rsrc_blob), rsec[1], rsrc_raw, RSRC_OFF)

    nsec = len(SECS)
    newho = img.sec_off + nsec * 40
    assert newho + 40 <= struct.unpack_from('<I', D, img.opt + 60)[0], '节头空间不足'
    nd[newho:newho + 8] = SECNAME
    struct.pack_into('<IIII', nd, newho + 8, len(blob), newsec_rva, cnstr_raw, cnstr_off)
    struct.pack_into('<I', nd, newho + 36, 0x60000020)          # CODE|EXECUTE|READ
    e_lfanew = struct.unpack_from('<I', D, 0x3C)[0]
    struct.pack_into('<H', nd, e_lfanew + 6, nsec + 1)          # NumberOfSections

    struct.pack_into('<II', nd, DDIR + 16, img.res_rva, len(rsrc_blob))
    if overlay:
        struct.pack_into('<II', nd, DDIR + 32, overlay_off, len(overlay))
    else:
        struct.pack_into('<II', nd, DDIR + 32, 0, 0)
    struct.pack_into('<I', nd, img.opt + 56,
                     align(newsec_rva + len(blob), SECALIGN))    # SizeOfImage

    # ---- PE 校验和 ----
    ck_off = img.opt + 64
    struct.pack_into('<I', nd, ck_off, 0)
    chk = 0
    for i in range(0, len(nd) - 1, 2):
        chk += struct.unpack_from('<H', nd, i)[0]
        chk = (chk & 0xFFFF) + (chk >> 16)
    if len(nd) % 2:
        chk += nd[-1]
        chk = (chk & 0xFFFF) + (chk >> 16)
    chk = (chk & 0xFFFF) + (chk >> 16)
    chk += len(nd)
    struct.pack_into('<I', nd, ck_off, chk & 0xFFFFFFFF)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, 'wb').write(bytes(nd))
    print("\n输出: %s (%d 字节, 原 %d)" % (out_path, len(nd), len(ORIG)))
    print("原 MD5: %s" % hashlib.md5(ORIG).hexdigest())
    print("新 MD5: %s" % hashlib.md5(bytes(nd)).hexdigest())

    if report_path:
        with open(report_path, 'w', encoding='utf-8') as f:
            import json
            json.dump({'target': target, 'out': out_path,
                       'newsec_rva': newsec_rva, 'cave_rva': cave_rva, 'cave_len': len(cave),
                       'loops': loops, 'mbtwc': mbtwc, 'mbtwc_how': how,
                       'relocated': len(newoff), 'inplace': len(inplace), 'skipped': len(skipped),
                       'patched_abs': p_abs, 'patched_lea': p_lea,
                       'dialog_hits': len(dlg_hits), 'unmatched': unmatched,
                       'strings': {hex(k): v[0] for k, v in targets.items()}},
                      f, ensure_ascii=False, indent=1)
    return out_path


# ================================================================ 6. 运行时自检
def verify(exe_path, timeout=6.0):
    u32 = ctypes.WinDLL("user32", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    u32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
    u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    u32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    u32.GetMenu.argtypes = [wt.HWND]
    u32.GetMenu.restype = wt.HMENU
    u32.GetMenuItemCount.argtypes = [wt.HMENU]
    u32.GetMenuItemCount.restype = ctypes.c_int
    u32.GetSubMenu.argtypes = [wt.HMENU, ctypes.c_int]
    u32.GetSubMenu.restype = wt.HMENU
    u32.GetMenuStringW.argtypes = [wt.HMENU, wt.UINT, wt.LPWSTR, ctypes.c_int, wt.UINT]

    ENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def find(pid):
        res = []

        def cb(h, _):
            p = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid:
                c = ctypes.create_unicode_buffer(64)
                u32.GetClassNameW(h, c, 64)
                res.append((h, c.value))
            return True
        u32.EnumWindows(ENUM(cb), 0)
        return res

    p = subprocess.Popen([exe_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    wins = find(p.pid)
    main = [h for h, c in wins if c == 'VOIDIMAGEVIEWER']
    ok = False
    detail = []
    if main:
        hm = u32.GetMenu(main[0])
        if hm:
            top = u32.GetMenuItemCount(hm)
            detail.append("顶级菜单 %d 项" % top)
            for i in range(top):
                sm = u32.GetSubMenu(hm, i)
                buf = ctypes.create_unicode_buffer(128)
                u32.GetMenuStringW(sm if sm else hm, i, buf, 128, 0x400)
                txt = buf.value
                detail.append("  [%d] %s" % (i, txt))
                if any('\u4e00' <= ch <= '\u9fff' for ch in txt):
                    ok = True
    try:
        p.terminate()
    except Exception:
        pass
    time.sleep(0.4)
    if p.poll() is None:
        subprocess.run(["taskkill", "/F", "/PID", str(p.pid)], capture_output=True)
    print("自检：主窗口 %s" % ("已创建" if main else "未找到"))
    for d in detail:
        print("  " + d)
    print("自检结论：%s" % ("菜单已为中文 ✅" if ok else "未检测到中文菜单 ⚠"))
    return ok


# ================================================================ main
def is_localized(path):
    try:
        img = PE(path)
    except Exception:
        return False
    return any(s[0].rstrip('\0') == '.cnstr' for s in img.secs)


def find_backup(target):
    import glob
    d = os.path.join(HERE, "备份")
    if not os.path.isdir(d):
        return None
    c = sorted(glob.glob(os.path.join(d, os.path.basename(target) + ".*.bak")))
    return c[-1] if c else None


def main():
    ap = argparse.ArgumentParser(description="Void Image Viewer 汉化包（版本自适应重建）")
    ap.add_argument("--target", default=DEFAULT_TARGET, help="原版 exe 路径")
    ap.add_argument("--out", default=os.path.join(HERE, "cn_out", "voidImageViewer.cn.exe"),
                    help="输出路径")
    ap.add_argument("--deploy", action="store_true", help="备份后覆盖目标 exe")
    ap.add_argument("--verify", action="store_true", help="生成后启动程序并读取菜单自检")
    ap.add_argument("--restore", action="store_true", help="从备份还原原始 exe 后退出")
    ap.add_argument("--keep-report", action="store_true", help="额外输出 rebuild_report.json")
    a = ap.parse_args()

    if not os.path.isfile(a.target):
        raise SystemExit("!! 找不到目标文件：%s" % a.target)

    if a.restore:
        bak = find_backup(a.target)
        if not bak:
            raise SystemExit("!! 未找到备份文件。")
        shutil.copy2(bak, a.target)
        print("已还原原始 exe：%s -> %s" % (bak, a.target))
        return

    src = a.target
    if is_localized(src):
        bak = find_backup(a.target)
        if not bak:
            raise SystemExit("!! 目标已是汉化版，且未找到备份原版。\n"
                             "   请先用安装包里的原始 exe 覆盖 %s 后再运行。" % a.target)
        print("[!] 目标已是汉化版，本次改用备份原版重建：%s\n" % bak)
        src = bak

    rep = os.path.join(HERE, "rebuild_report.json") if a.keep_report else None
    out = build(src, a.out, rep)

    if a.deploy:
        if not is_localized(a.target):
            bak_dir = os.path.join(HERE, "备份")
            os.makedirs(bak_dir, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            bak = os.path.join(bak_dir, "%s.%s.bak" % (os.path.basename(a.target), stamp))
            shutil.copy2(a.target, bak)
            print("已备份原版 -> %s" % bak)
        shutil.copy2(out, a.target)
        print("已部署 -> %s" % a.target)
        out = a.target

    if a.verify:
        print()
        verify(out)


if __name__ == "__main__":
    main()
