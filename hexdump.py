import re
SRC = r'C:\Program Files\voidImageViewer\voidImageViewer.exe'
d = open(SRC, 'rb').read()
seg = d[0x41800:0x43400]
# print as ascii with offsets
for i in range(0, len(seg), 16):
    chunk = seg[i:i+16]
    off = 0x41800 + i
    asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
    print('%06x  %-47s  %s' % (off, ' '.join('%02x' % c for c in chunk), asc))
