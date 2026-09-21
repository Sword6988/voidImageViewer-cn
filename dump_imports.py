import struct, sys, re

SRC = r'C:\Program Files\voidImageViewer\voidImageViewer.exe'
d = open(SRC, 'rb').read()
e = struct.unpack_from('<I', d, 0x3C)[0]
nsec, optsize = struct.unpack_from('<HH', d, e + 4 + 2)[0], struct.unpack_from('<H', d, e + 4 + 16)[0]
opt = e + 24
ddir = opt + 112
nimp = struct.unpack_from('<I', d, ddir + 8)[0]  # DataDirectory[1] import RVA
imp_rva = struct.unpack_from('<I', d, ddir + 8)[0]
secs = []
so = opt + optsize
for i in range(nsec):
    o = so + i * 40
    name = d[o:o+8].rstrip(b'\0').decode('latin1')
    vsz, va, rsz, raw = struct.unpack_from('<IIII', d, o + 8)
    secs.append((name, va, vsz, raw, rsz))

def r2o(rva):
    for n, va, vsz, raw, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)

p = r2o(imp_rva)
print('===== IMPORTS =====')
while True:
    oft, ts, fc, nameRva, fta = struct.unpack_from('<IIIII', d, p)
    if nameRva == 0:
        break
    no = r2o(nameRva)
    dll = d[no:d.index(b'\0', no)].decode('latin1')
    funcs = []
    q = r2o(oft or fta)
    while True:
        v = struct.unpack_from('<Q', d, q)[0]
        if v == 0:
            break
        if v & 0x8000000000000000:
            funcs.append('ord#%d' % (v & 0xFFFF))
        else:
            fo = r2o(v & 0x7FFFFFFF)
            funcs.append(d[fo+2:d.index(b'\0', fo+2)].decode('latin1'))
        q += 8
    print('%-24s %s' % (dll, ', '.join(funcs)))
    p += 20

# Is it Unicode? check for MessageBoxA vs W
allf = b''
p = r2o(imp_rva)
while True:
    oft, ts, fc, nameRva, fta = struct.unpack_from('<IIIII', d, p)
    if nameRva == 0:
        break
    no = r2o(nameRva)
    dll = d[no:d.index(b'\0', no)].decode('latin1')
    q = r2o(oft or fta)
    while True:
        v = struct.unpack_from('<Q', d, q)[0]
        if v == 0:
            break
        if not (v & 0x8000000000000000):
            fo = r2o(v & 0x7FFFFFFF)
            allf += d[fo+2:d.index(b'\0', fo+2)] + b' '
        q += 8
    p += 20
print()
print('MessageBoxA' in allf.decode(), 'MessageBoxW' in allf.decode())
print('W-funcs:', allf.decode().count('W '), 'A-funcs:', allf.decode().count('A '))
