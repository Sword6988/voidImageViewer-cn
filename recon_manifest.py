# -*- coding: utf-8 -*-
"""提取 manifest 资源 + PE 关键头字段 + COMCTL32 导入明细。"""
import struct

PATH = r"D:\Desktop\软件汉化\backup\voidImageViewer.exe.orig"
OUT = r"D:\Desktop\软件汉化\out"


def parse(path):
    d = open(path, "rb").read()
    e = struct.unpack_from("<I", d, 0x3C)[0]
    coff = e + 4
    machine, nsec, _, _, _, optsz, chars = struct.unpack_from("<HHIIIHH", d, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", d, opt)[0]
    is64 = magic == 0x20B
    entry = struct.unpack_from("<I", d, opt + 16)[0]
    imagebase = struct.unpack_from("<Q", d, opt + 24)[0] if is64 else struct.unpack_from("<I", d, opt + 28)[0]
    sectalign = struct.unpack_from("<I", d, opt + 32)[0]
    filealign = struct.unpack_from("<I", d, opt + 36)[0]
    dllchar = struct.unpack_from("<H", d, opt + (0x46 if is64 else 0x46))[0]
    dd = opt + (112 if is64 else 96)
    dirs = [struct.unpack_from("<II", d, dd + i * 8) for i in range(16)]
    sec_off = opt + optsz
    secs = []
    for i in range(nsec):
        o = sec_off + i * 40
        nm = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vsize, vaddr, rawsz, rawptr = struct.unpack_from("<IIII", d, o + 8)
        ch = struct.unpack_from("<I", d, o + 36)[0]
        secs.append((nm, vaddr, vsize, rawptr, rawsz, ch))
    return d, is64, entry, imagebase, sectalign, filealign, dllchar, dirs, secs


d, is64, entry, imagebase, sal, fal, dllchar, dirs, secs = parse(PATH)
print("ImageBase       = %#x" % imagebase)
print("EntryPoint RVA  = %#x" % entry)
print("SectionAlign    = %#x  FileAlign = %#x" % (sal, fal))
print("DllCharacteristics = %#06x  -> %s" % (dllchar, ", ".join(
    n for bit, n in [(0x0001, "HIGH_ENTROPY_VA"), (0x0020, "HIGH_ENTROPY_VA"),
                     (0x0040, "DYNAMIC_BASE"), (0x0080, "FORCE_INTEGRITY"),
                     (0x0100, "NX_COMPAT"), (0x0200, "NO_ISOLATION"),
                     (0x0400, "NO_SEH"), (0x0800, "NO_BIND"),
                     (0x1000, "APPCONTAINER"), (0x2000, "WDM_DRIVER"),
                     (0x4000, "GUARD_CF"), (0x8000, "TERMINAL_SERVER_AWARE")]
    if dllchar & bit)))
print("ImageBase 是否等于默认 0x140000000:", imagebase == 0x140000000)

# --- 资源目录 -> 找 RT_MANIFEST(24) ---
def r2o(rva):
    for n, va, vs, rp, rs, ch in secs:
        if va <= rva < va + max(vs, rs):
            return rp + (rva - va)
    return None


def parse_res(base_rva, level=0, prefix=""):
    """返回 [(type_id_or_name, name_id, lang, data_rva, size)]"""
    found = []
    o = r2o(base_rva)
    nname, nid = struct.unpack_from("<HH", d, o + 12)
    total = nname + nid
    for i in range(total):
        eo = o + 16 + i * 8
        name, off = struct.unpack_from("<II", d, eo)
        if name & 0x80000000:
            sub = base_rva + (name & 0x7FFFFFFF)
            # UTF-16 name
            so = r2o(sub)
            ln = struct.unpack_from("<H", d, so)[0]
            label = d[so + 2:so + 2 + ln * 2].decode("utf-16-le", "replace")
        else:
            label = name
        if off & 0x80000000:
            found += parse_res(base_rva + (off & 0x7FFFFFFF), level + 1, prefix + "/" + str(label))
        else:
            do_ = r2o(base_rva + off)
            drva, dsize, cp, _ = struct.unpack_from("<IIII", d, do_)
            found.append((prefix + "/" + str(label), drva, dsize))
    return found


res_rva, res_size = dirs[2]
items = parse_res(res_rva)
print("\n=== 资源条目（路径/数据RVA/大小）===")
for p, rva, sz in items:
    print("  %-24s rva=%#x size=%d" % (p, rva, sz))

print("\n=== RT_MANIFEST 内容 ===")
mani = [it for it in items if it[0].startswith("/24/")]
if not mani:
    print("  (无 RT_MANIFEST -> 程序不带清单，COMCTL32 走普通搜索顺序 = 可劫持)")
else:
    for p, rva, sz in mani:
        o = r2o(rva)
        raw = d[o:o + sz]
        txt = raw.decode("utf-8", "replace")
        print(txt)
        open(OUT + r"\manifest.xml", "w", encoding="utf-8").write(txt)

print("=== COMCTL32 导入明细 ===")
print(open(OUT + r"\imports_IMPORT.txt", encoding="utf-8").read().split("\n\n")[0])
