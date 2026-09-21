import sys, os, json, struct
sys.path.insert(0, r'C:\Users\Shibeng\.workbuddy\skills\win32-exe-localizer\scripts')
from pe_res_engine import PE, load_resources, parse_menu, parse_dialog

SRC = r'C:\Program Files\voidImageViewer\voidImageViewer.exe'
pe = PE(SRC)
res = load_resources(pe)
print('total resources:', len(res))
for r in sorted(res, key=lambda x: (str(x.kind), str(x.name))):
    print('%-14s name=%-8s lang=%-6s size=%-6d rva=0x%x' % (r.kind, r.name, r.lang, r.size, r.rva))

print('\n===== MENUS =====')
for r in res:
    if r.kind == 'MENU':
        try:
            m = parse_menu(r.blob)
        except Exception as e:
            print('MENU', r.name, 'parse error', e)
            continue
        print('--- MENU %s (%d items)' % (r.name, len(m['items'])))
        def walk(items, d=0):
            for it in items:
                print('   ' * d + '[%s] id=%s flags=0x%x text=%r' % ('pop' if it.sub is not None else 'cmd', it.mid, it.opt, it.text))
                if it.sub:
                    walk(it.sub, d + 1)
        walk(m['items'])

print('\n===== DIALOGS =====')
for r in res:
    if r.kind == 'DIALOG':
        try:
            d, consumed = parse_dialog(r.blob)
        except Exception as e:
            print('DLG', r.name, 'parse error', e)
            continue
        print('--- DIALOG %s ex=%s title=%r  size=%dx%d items=%d consumed=%d/%d' % (
            r.name, d.is_ex, d.title, d.cx, d.cy, len(d.items), consumed, r.size))
        for it in d.items:
            print('    id=%-5s cls=%-22r title=%r' % (it.id, it.cls, it.title))
