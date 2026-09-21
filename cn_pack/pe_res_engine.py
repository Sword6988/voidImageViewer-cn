"""FCEUX Win32 localization engine: parse / translate / rebuild PE resources."""
import struct, json, os, shutil

# ---------------------------------------------------------------- PE
class PE:
    def __init__(self, path):
        self.path = path
        self.data = bytearray(open(path, 'rb').read())
        d = self.data
        e = struct.unpack_from('<I', d, 0x3C)[0]
        coff = e + 4
        self.nsec = struct.unpack_from('<H', d, coff + 2)[0]
        self.optsize = struct.unpack_from('<H', d, coff + 16)[0]
        self.opt = coff + 20
        self.ddir = self.opt + 112
        self.secs = []
        so = self.opt + self.optsize
        self.sec_off = so
        for i in range(self.nsec):
            o = so + i * 40
            name = d[o:o + 8].rstrip(b'\0').decode('latin1')
            vsz, va, rsz, raw = struct.unpack_from('<IIII', d, o + 8)
            self.secs.append([name, va, vsz, raw, rsz, o])
        self.res_rva, self.res_size = struct.unpack_from('<II', d, self.ddir + 16)

    def sec(self, name):
        for s in self.secs:
            if s[0] == name:
                return s

    def rva2off(self, rva):
        for n, va, vsz, raw, rsz, o in self.secs:
            if va <= rva < va + max(vsz, rsz):
                return raw + (rva - va)

    def save(self, path):
        open(path, 'wb').write(bytes(self.data))


TYPE_NAMES = {1: 'CURSOR', 2: 'BITMAP', 3: 'ICON', 4: 'MENU', 5: 'DIALOG', 6: 'STRING',
              9: 'ACCELERATOR', 10: 'RCDATA', 12: 'GROUP_CURSOR', 14: 'GROUP_ICON',
              16: 'VERSION', 24: 'MANIFEST'}


class Res:
    """One leaf resource."""

    def __init__(self, type_, name, lang, rva, size, blob):
        self.type, self.name, self.lang = type_, name, lang
        self.rva, self.size, self.blob = rva, size, blob
        self.new_blob = blob            # set by translators
        self.is_str = isinstance(type_, str)

    @property
    def kind(self):
        if self.is_str:
            return self.type
        return TYPE_NAMES.get(self.type, 'TYPE%d' % self.type)

    def key(self):
        return "%s/%s/%s" % (self.kind, self.name, self.lang)


def load_resources(pe):
    sec = pe.sec('.rsrc')
    base_va, base_raw = sec[1], sec[3]

    def o(x):
        return base_raw + (x - base_va)

    out = []

    def walk(rva, level, t, nm):
        p = o(rva)
        n_named, n_id = struct.unpack_from('<HH', pe.data, p + 12)
        for i in range(n_named + n_id):
            e = p + 16 + i * 8
            name, sub = struct.unpack_from('<II', pe.data, e)
            if name & 0x80000000:
                no = o(base_va + (name & 0x7FFFFFFF))
                ln = struct.unpack_from('<H', pe.data, no)[0]
                label = pe.data[no + 2:no + 2 + ln * 2].decode('utf-16-le')
            else:
                label = name
            if sub & 0x80000000:
                if level == 0:
                    walk(base_va + (sub & 0x7FFFFFFF), 1, label, None)
                elif level == 1:
                    walk(base_va + (sub & 0x7FFFFFFF), 2, t, label)
                else:
                    walk(base_va + (sub & 0x7FFFFFFF), 3, t, nm)
            else:
                do = o(base_va + sub)
                drva, dsize = struct.unpack_from('<II', pe.data, do)
                t2, nm2, lg2 = (t, label, None) if level == 1 else (t, nm, label)
                out.append(Res(t2, nm2, lg2, drva, dsize, bytes(pe.data[o(drva):o(drva) + dsize])))

    walk(pe.res_rva, 0, None, None)
    return out


def build_rsrc(resources, res_rva):
    """Serialise resource tree into a byte blob (offsets relative to blob start)."""
    # group: type -> name -> lang -> Res
    tree = {}
    order = []
    for r in resources:
        tk = r.type
        if tk not in tree:
            tree[tk] = {}
            order.append(tk)
        nk = r.name
        tree[tk].setdefault(nk, {})
        tree[tk][nk][r.lang] = r

    dirblob = bytearray()
    names_blob = bytearray()

    def align(b, n=4):
        while len(b) % n:
            b.append(0)

    # ---- pass 1: allocate directory space, fill later
    # We build recursively, recording (offset_in_dirblob, child_offsets)
    root_dir_off = 0

    def build_dir(entries, dirbuf, namebuf, base_off_names):
        """entries: list of (label, is_named, child_builder or Res)
        Returns offset where this directory will be written (relative to resource base)."""
        # We need offsets of names (into namebuf at absolute resource offsets) and children.
        raise NotImplementedError

    # simpler: two-phase with explicit offsets
    # phase A: decide directory offsets
    dirs = []           # list of dict(node, offset)
    dirsize_cursor = [0]

    def alloc_dir():
        off = dirsize_cursor[0]
        dirsize_cursor[0] += 16
        return off

    def alloc_name(s):
        # append later; remember placeholder
        return s

    # Build an explicit structure first
    class N:
        __slots__ = ('label', 'named', 'kind', 'off', 'name_off', 'children', 'res')

        def __init__(self, label, named, kind):
            self.label, self.named, self.kind = label, named, kind
            self.off = None
            self.name_off = None
            self.children = []
            self.res = None

    types_nodes = []
    for tk in order:
        t_is_str = isinstance(tk, str)
        tn = N(tk, t_is_str, 'type')
        for nk in tree[tk]:
            n_is_str = isinstance(nk, str)
            nn = N(nk, n_is_str, 'name')
            for lg in tree[tk][nk]:
                ln = N(lg, False, 'lang')
                ln.res = tree[tk][nk][lg]
                nn.children.append(ln)
            tn.children.append(nn)
        types_nodes.append(tn)

    # serialize directories in DFS order; entries = named first then ids ascending
    dirbuf = bytearray()
    namebuf = bytearray()
    dirbuf_off = []          # offsets in dirbuf where each directory starts

    def layout(node, is_root=False):
        """returns (dir_offset_in_dirbuf)"""
        off = len(dirbuf)
        node.off = off
        entries = node.children
        named = [c for c in entries if c.named]
        ids = [c for c in entries if not c.named]
        ids.sort(key=lambda c: c.label)
        seq = named + ids
        dirbuf.extend(b'\0' * (16 + 8 * len(seq)))
        for i, c in enumerate(seq):
            # name / id
            if c.named:
                # name string goes in namebuf, absolute offset patched later
                name_off = len(namebuf)
                bs = c.label.encode('utf-16-le')
                namebuf.extend(struct.pack('<H', len(c.label)) + bs)
                while len(namebuf) % 4:
                    namebuf.append(0)
                c.name_off = name_off
            # recurse to know child offset
            if c.kind == 'lang':
                sub = c.res
            else:
                layout(c)
        return off

    # root dir is at 0 by construction
    root = N(None, False, 'root')
    root.children = types_nodes
    layout(root)

    # ---- phase B: data area
    databuf = bytearray()
    data_entry_offsets = []

    def place_data(res):
        while len(databuf) % 4:
            databuf.append(0)
        off = len(databuf) + 1  # placeholder; fixed after we know data_area_start
        return off

    # compute dir area size = len(dirbuf) + len(namebuf)
    # final layout: [dirbuf][namebuf][data entries...][blobs...]
    # write pass: compute data entry area first (16 bytes each, in same order as traversal)
    leaves = []
    for tk in order:
        for nk in tree[tk]:
            for lg in tree[tk][nk]:
                leaves.append(tree[tk][nk][lg])

    ndata = len(leaves)
    dir_area = len(dirbuf) + len(namebuf)
    data_entries_start = dir_area
    blobs_start = data_entries_start + 16 * ndata

    blobbuf = bytearray()
    entry_pos = {}
    for i, r in enumerate(leaves):
        while len(blobbuf) % 4:
            blobbuf.append(0)
        entry_pos[id(r)] = blobs_start + len(blobbuf)
        blobbuf.extend(r.new_blob)

    total = blobs_start + len(blobbuf)
    out = bytearray(total)

    # header
    def header(n_named, n_id):
        return struct.pack('<IIHHHH', 0, 0, 0, 0, n_named, n_id)

    # write dirs
    def write_dir(node, is_root=False):
        entries = node.children
        named = [c for c in entries if c.named]
        ids = [c for c in entries if not c.named]
        ids.sort(key=lambda c: c.label)
        seq = named + ids
        base = node.off
        out[base:base + 16] = struct.pack('<IIHHHH', 0, 0, 0, 0, len(named), len(ids))
        for i, c in enumerate(seq):
            e = base + 16 + i * 8
            if c.named:
                nabs = len(dirbuf) + c.name_off
                struct.pack_into('<II', out, e, 0x80000000 | nabs, 0)
            else:
                struct.pack_into('<II', out, e, c.label, 0)
            if c.kind == 'lang':
                doff = data_entries_start + 16 * leaves.index(c.res)
                struct.pack_into('<I', out, e + 4, doff)      # data entry: high bit MUST be clear
            else:
                struct.pack_into('<I', out, e + 4, 0x80000000 | c.off)
        for c in seq:
            if c.kind != 'lang':
                write_dir(c)

    write_dir(root)
    out[len(dirbuf):len(dirbuf) + len(namebuf)] = namebuf

    # data entries
    for i, r in enumerate(leaves):
        e = data_entries_start + 16 * i
        struct.pack_into('<IIII', out, e, res_rva + entry_pos[id(r)], len(r.new_blob), 0, 0)

    out[blobs_start:] = blobbuf
    return bytes(out)


# ---------------------------------------------------------------- MENU (classic)
def read_wstr(buf, p):
    s = []
    while True:
        c = struct.unpack_from('<H', buf, p)[0]
        p += 2
        if c == 0:
            break
        s.append(chr(c))
    return ''.join(s), p


def enc_wstr(s):
    return s.encode('utf-16-le') + b'\0\0'


class MItem:
    def __init__(self, opt, mid, text):
        self.opt, self.mid, self.text = opt, mid, text
        self.sub = None


def parse_menu(blob):
    ver, hdr = struct.unpack_from('<HH', blob, 0)
    items, p = _menu_items(blob, 4 + hdr)
    return dict(ver=ver, hdr=hdr, items=items, end=p)


def _menu_items(buf, p):
    out = []
    while True:
        opt = struct.unpack_from('<H', buf, p)[0]
        p += 2
        if opt & 0x10:
            text, p = read_wstr(buf, p)
            it = MItem(opt, None, text)
            it.sub, p = _menu_items(buf, p)
        else:
            mid = struct.unpack_from('<H', buf, p)[0]
            p += 2
            text, p = read_wstr(buf, p)
            it = MItem(opt, mid, text)
        out.append(it)
        if opt & 0x80:
            return out, p


def enc_menu(m):
    return struct.pack('<HH', m['ver'], m['hdr']) + _enc_items(m['items'])


def _enc_items(items):
    out = b''
    for it in items:
        out += struct.pack('<H', it.opt)
        if it.opt & 0x10:
            out += enc_wstr(it.text)
            out += _enc_items(it.sub)
        else:
            out += struct.pack('<H', it.mid) + enc_wstr(it.text)
    return out


# ---------------------------------------------------------------- DIALOG
class DItem:
    def __init__(self, helpid, style, exstyle, x, y, cx, cy, cid, cls, title, cdata):
        self.helpid = helpid
        self.style, self.exstyle = style, exstyle
        self.x, self.y, self.cx, self.cy = x, y, cx, cy
        self.id, self.cls, self.title, self.cdata = cid, cls, title, cdata


class Dlg:
    def __init__(self):
        self.items = []
        self.style = self.exstyle = 0
        self.helpID = 0
        self.x = self.y = self.cx = self.cy = 0
        self.menu = self.cls = self.title = None
        self.pointsize = None
        self.weight = self.italic = self.charset = None
        self.typeface = None
        self.is_ex = False
        self.pad = b''


def _ord_or_str(buf, p):
    v = struct.unpack_from('<H', buf, p)[0]
    if v == 0:
        return ('empty', None), p + 2
    if v == 0xFFFF:
        o = struct.unpack_from('<H', buf, p + 2)[0]
        return ('ord', o), p + 4
    s, p2 = read_wstr(buf, p)
    return ('str', s), p2


def _enc_ord_or_str(f):
    kind, val = f
    if kind == 'empty':
        return b'\0\0'
    if kind == 'ord':
        return struct.pack('<HH', 0xFFFF, val)
    return enc_wstr(val)


def parse_dialog(blob):
    """DLGTEMPLATE / DLGTEMPLATEEX."""
    d = Dlg()
    p = 0
    v, sig = struct.unpack_from('<HH', blob, p)
    if v == 1 and sig == 0xFFFF:
        d.is_ex = True
        d.helpID = struct.unpack_from('<I', blob, p + 4)[0]
        d.exstyle = struct.unpack_from('<I', blob, p + 8)[0]
        d.style = struct.unpack_from('<I', blob, p + 12)[0]
        p = 16
    else:
        d.style = struct.unpack_from('<I', blob, 0)[0]
        d.exstyle = struct.unpack_from('<I', blob, 4)[0]
        p = 8
    cdit, x, y, cx, cy = struct.unpack_from('<Hhhhh', blob, p)
    p += 10
    d.x, d.y, d.cx, d.cy = x, y, cx, cy
    d.menu, p = _ord_or_str(blob, p)
    d.cls, p = _ord_or_str(blob, p)
    d.title, p = _ord_or_str(blob, p)
    if d.style & 0x40:                       # DS_SETFONT
        d.pointsize = struct.unpack_from('<H', blob, p)[0]
        p += 2
        if d.is_ex:
            d.weight, d.italic, d.charset = struct.unpack_from('<HBB', blob, p)
            p += 4
        d.typeface, p = read_wstr(blob, p)
    for _ in range(cdit):
        while p % 4:
            p += 1
        helpid = 0
        if d.is_ex:
            helpid, iex, ist = struct.unpack_from('<III', blob, p)
            p += 12
            ix, iy, icx, icy, iid = struct.unpack_from('<hhhhI', blob, p)
            p += 12
        else:
            ist, iex = struct.unpack_from('<II', blob, p)
            p += 8
            ix, iy, icx, icy = struct.unpack_from('<hhhh', blob, p)
            p += 8
            iid = struct.unpack_from('<H', blob, p)[0]
            p += 2
        icls, p = _ord_or_str(blob, p)
        ititle, p = _ord_or_str(blob, p)
        cdata = None
        cs = struct.unpack_from('<H', blob, p)[0]
        p += 2
        if cs:
            cdata = bytes(blob[p:p + cs])
            p += cs
        d.items.append(DItem(helpid, ist, iex, ix, iy, icx, icy, iid, icls, ititle, cdata))
    d.pad = bytes(blob[p:])                  # trailing DWORD padding
    return d, p


def enc_dialog(d):
    out = bytearray()
    if d.is_ex:
        out += struct.pack('<HHII', 1, 0xFFFF, d.helpID, d.exstyle)
        out += struct.pack('<I', d.style)
    else:
        out += struct.pack('<II', d.style, d.exstyle)
    out += struct.pack('<Hhhhh', len(d.items), d.x, d.y, d.cx, d.cy)
    out += _enc_ord_or_str(d.menu)
    out += _enc_ord_or_str(d.cls)
    out += _enc_ord_or_str(d.title)
    if d.style & 0x40:
        out += struct.pack('<H', d.pointsize)
        if d.is_ex:
            out += struct.pack('<HBB', d.weight, d.italic, d.charset)
        out += enc_wstr(d.typeface)
    for it in d.items:
        while len(out) % 4:
            out.append(0)
        if d.is_ex:
            out += struct.pack('<III', it.helpid, it.exstyle, it.style)
            out += struct.pack('<hhhhI', it.x, it.y, it.cx, it.cy, it.id)
        else:
            out += struct.pack('<II', it.style, it.exstyle)
            out += struct.pack('<hhhh', it.x, it.y, it.cx, it.cy)
            out += struct.pack('<H', it.id)
        out += _enc_ord_or_str(it.cls)
        out += _enc_ord_or_str(it.title)
        if it.cdata:
            out += struct.pack('<H', len(it.cdata)) + it.cdata
        else:
            out += b'\0\0'
    out += d.pad
    return bytes(out)
