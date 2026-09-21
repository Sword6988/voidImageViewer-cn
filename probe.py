import struct
SRC = r'C:\Program Files\voidImageViewer\voidImageViewer.exe'
d = open(SRC, 'rb').read()

words = ['File', 'Edit', 'View', 'Help', 'Options', 'About', 'Slideshow', 'Zoom',
         'Rotate', 'Delete', 'Copy', 'Paste', 'Fullscreen', 'Navigate', 'Animation',
         'Wallpaper', 'Rename', 'Properties', 'Print', 'Exit', 'Shuffle', 'Sort',
         'Pan', 'Scan', 'Command Line', 'Home Page', 'Donate', 'Caption', 'Status']

for w in words:
    hits = {}
    for enc, name in ((w.encode('utf-16-le'), 'utf16'), (w.encode('latin1'), 'ansi')):
        pos = 0
        c = 0
        first = []
        while True:
            p = d.find(enc, pos)
            if p < 0:
                break
            c += 1
            if len(first) < 6:
                first.append(hex(p))
            pos = p + 1
        if c:
            hits[name] = (c, first)
    print('%-16s %s' % (w, hits if hits else 'NONE'))
