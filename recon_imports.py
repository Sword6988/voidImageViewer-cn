# -*- coding: utf-8 -*-
"""侦察 voidImageViewer ORIGINAL 的导入结构，判断 DLL 劫持/代理可行性。"""
import struct
import sys

PATH = r"D:\Desktop\软件汉化\backup\voidImageViewer.exe.orig"


def main():
    d = open(PATH, "rb").read()
    e_lfanew = struct.unpack_from("<I", d, 0x3C)[0]
    assert d[e_lfanew:e_lfanew + 4] == b"PE\0\0"
    coff = e_lfanew + 4
    machine, nsec, _, _, _, optsz, chars = struct.unpack_from("<HHIIIHH", d, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", d, opt)[0]
    is64 = magic == 0x20B
    print("machine=%04x nsec=%d magic=%04x" % (machine, nsec, magic))

    # DataDirectory
    dd_off = opt + (112 if is64 else 96)
    dirs = []
    for i in range(16):
        rva, size = struct.unpack_from("<II", d, dd_off + i * 8)
        dirs.append((rva, size))

    # sections
    sec_off = opt + optsz
    secs = []
    for i in range(nsec):
        o = sec_off + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vsize, vaddr, rawsz, rawptr = struct.unpack_from("<IIII", d, o + 8)
        secs.append((name, vaddr, vsize, rawptr, rawsz))
    print("sections:", [(s[0], hex(s[1]), hex(s[4])) for s in secs])

    def r2o(rva):
        for n, va, vs, rp, rs in secs:
            if va <= rva < va + max(vs, rs):
                return rp + (rva - va)
        return None

    def cstr(off):
        if off is None:
            return None
        end = d.find(b"\0", off)
        return d[off:end].decode("latin1", "replace")

    def read_imports(rva, size, label):
        print("\n=== %s (RVA %#x, size %d) ===" % (label, rva, size))
        if not rva or not size:
            print("  (空)")
            return []
        o = r2o(rva)
        names = []
        while True:
            ent = d[o:o + 20]
            if len(ent) < 20 or ent == b"\0" * 20:
                break
            oft, ts, fc, name_rva, iat = struct.unpack("<IIIII", ent)
            dll = cstr(r2o(name_rva))
            names.append(dll)
            thunk_rva = oft if oft else iat
            to = r2o(thunk_rva)
            funcs = []
            step = 8 if is64 else 4
            while to is not None:
                val = struct.unpack_from("<Q" if is64 else "<I", d, to)[0]
                if val == 0:
                    break
                if is64 and (val & 0x8000000000000000):
                    funcs.append("#%d" % (val & 0xFFFF))
                elif not is64 and (val & 0x80000000):
                    funcs.append("#%d" % (val & 0x7FFFFFFF))
                else:
                    fname = cstr(r2o((val & 0x7FFFFFFF) if not is64 else (val & 0x7FFFFFFF)))
                    funcs.append(fname)
                to += step
            print("  %-22s %3d 个导出" % (dll, len(funcs)))
            with open(r"D:\Desktop\软件汉化\out\imports_%s.txt" % label, "a", encoding="utf-8") as f:
                f.write("[%s]\n" % dll)
                for fn in funcs:
                    f.write("    %s\n" % fn)
                f.write("\n")
            o += 20
        return names

    imp = read_imports(*dirs[1], "IMPORT")
    dl = read_imports(*dirs[13], "DELAY_IMPORT")

    print("\n=== 关键目录 ===")
    for idx, nm in [(0, "Export"), (1, "Import"), (2, "Resource"), (4, "Certificate"),
                    (5, "BaseReloc"), (9, "TLS"), (10, "LoadConfig"), (13, "DelayImport")]:
        rva, size = dirs[idx]
        print("  %-12s RVA=%-10s size=%d" % (nm, hex(rva), size))

    # LoadConfig: 是否存在 SEH/CFG，及 GuardCFFunctionTable
    print("\n=== 是否调用 SetDefaultDllDirectories / SetDllDirectory / AddDllDirectory ===")
    for k in ["SetDefaultDllDirectories", "SetDllDirectoryA", "SetDllDirectoryW",
              "AddDllDirectory", "LoadLibraryA", "LoadLibraryW", "LoadLibraryExW",
              "GetModuleFileNameW", "MultiByteToWideChar", "SetDefaultDllDirectories"]:
        hit = d.find(k.encode() + b"\0")
        print("  %-30s %s" % (k, "命中" if hit > 0 else "-"))

    print("\n=== Import DLL 汇总 ===")
    allnames = (imp or []) + (dl or [])
    for n in allnames:
        print("  ", n)


if __name__ == "__main__":
    main()
