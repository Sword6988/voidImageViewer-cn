# -*- coding: utf-8 -*-
"""生成 Void Image Viewer 汉化对照表（HTML + JSON）
   逐项列出：分类 / 所在界面位置或资源标识 / 原文 / 中文译文
"""
import json, os, re, sys, html

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
sys.path.insert(0, HERE)
import translations as T

TR = T.merged()                       # en -> (zh, area)
REV = {}
for en, (zh, area) in TR.items():
    REV.setdefault(zh, en)
KEEP = T.KEEP
report = json.load(open(os.path.join(OUT, 'build_report.json'), encoding='utf-8'))
RVA_OF = {}
for rva, info in report['strings'].items():
    RVA_OF.setdefault(info['en'], []).append((rva, info['enc'], info.get('newrva')))
AREA_OF = {k: v[1] for k, v in TR.items()}

# ---------------------------------------------------------------- 解析运行时菜单树
probe = open(os.path.join(OUT, 'rt_cn', 'cn2_probe.txt'), encoding='utf-8').read()
menu_block = probe.split('===== 菜单栏 =====')[1].split('--- 截图 ---')[0]
MENU_PATH = {}          # en -> 中文菜单路径
stack = []
for line in menu_block.splitlines():
    if not line.strip() or '{id=' not in line:
        continue
    ind = len(line) - len(line.lstrip(' '))
    label = line.strip().split('\t')[0]
    label = re.sub(r'\s*\{id=\d+\}\s*$', '', label).strip()
    if not label:
        continue
    lvl = ind // 2
    stack = stack[:lvl]
    path = stack + [label]
    stack = path
    en = REV.get(label)
    if en:
        MENU_PATH[en] = ' > '.join(path)

# ---------------------------------------------------------------- 解析对话框内的列表项归属
DLGNAME = {101: '选项 · 常规页', 106: '选项对话框', 107: '选项 · 视图页', 109: '设置自定义速率对话框',
           110: '选项 · 控件页', 121: '关于对话框', 123: '编辑键盘快捷键对话框', 127: '重命名对话框',
           128: '跳转到对话框', 129: '搜索 Everything 对话框'}
aux = probe.split('=== DIALOG options')[1].split('=== DIALOG about')[0]
COMBO_LOC = {}
last_static = ''
for line in aux.splitlines():
    m = re.search(r"\[Static\] '(.*?)'", line)
    if m:
        last_static = m.group(1)
    m = re.search(r"\[(ComboBox|ListBox)\] ''  <= \[(.*)\]$", line.strip())
    if m:
        items = re.findall(r"'((?:[^'\\]|\\.)*)'", m.group(2))
        for it in items:
            en = REV.get(it)
            if en and en not in COMBO_LOC:
                COMBO_LOC[en] = last_static or '选项 · 控件页'

rows = []
used = set()


def add(cat, loc, en, note=''):
    if en in used:
        return
    zh, area = TR[en]
    used.add(en)
    rows.append({'cat': cat, 'loc': loc, 'en': en, 'zh': zh, 'note': note})


# 1) 主菜单 / 子菜单项
for en in list(TR):
    if en in MENU_PATH:
        add('主菜单 / 菜单项', '菜单栏：' + MENU_PATH[en], en)

# 2) 各属性页 / 对话框内的下拉列表项
for en, loc in COMBO_LOC.items():
    if en not in used:
        add('选项对话框 · 下拉列表与列表项', '选项对话框 → ' + loc, en)

# 3) 对话框资源（DIALOG n）标题与控件
for did, where, en, zh in report['dlg_hits']:
    if en in used:
        continue
    if where == 'title':
        loc = '%s（DIALOG %d 标题）' % (DLGNAME.get(did, ''), did)
    else:
        loc = '%s（DIALOG %d 控件 %s）' % (DLGNAME.get(did, ''), did, where.replace('id=', 'ID '))
    used.add(en)
    rows.append({'cat': '对话框资源（DIALOG）', 'loc': loc, 'en': en, 'zh': zh, 'note': ''})

# 4) 其余按 translations.py 的归类
CATMAP = {'状态栏/工具栏/提示': '状态栏 / 工具栏提示 / 错误信息',
          '文件对话框/文件类型': '文件对话框 / 文件类型',
          '关于/帮助正文': '关于 · 命令行选项（帮助正文）',
          '选项设置': '选项对话框 · 设置项',
          '主菜单/菜单项': '主菜单 / 菜单项',
          '内部调试信息': '内部调试信息（仅开发可见）'}
LOC_DEFAULT = {'状态栏/工具栏/提示': '状态栏 / 工具栏 / 消息提示（程序内字符串常量）',
               '文件对话框/文件类型': '打开 / 移动 / 复制 文件对话框',
               '关于/帮助正文': '帮助 > 命令行选项 对话框正文',
               '选项设置': '选项对话框',
               '主菜单/菜单项': '菜单栏（按条件显示的菜单项）',
               '内部调试信息': '状态栏调试输出（需启用调试项）'}
for en, (zh, area) in TR.items():
    if en in used:
        continue
    add(CATMAP.get(area, area), LOC_DEFAULT.get(area, '程序界面文本'), en)

# 5) 补充：为每条附加 RVA / 资源标识
for r in rows:
    info = RVA_OF.get(r['en'])
    if info:
        r['note'] = 'RVA ' + ' / '.join(x[0] for x in info) + ('' if info[0][1] == 'ansi' else ' (UTF-16)')
    elif r['en'] in T.EXTRA_BY_RVA:
        r['note'] = 'RVA 0x0443a7'

ORDER = ['主菜单 / 菜单项', '选项对话框 · 下拉列表与列表项', '选项对话框 · 设置项', '对话框资源（DIALOG）',
         '状态栏 / 工具栏提示 / 错误信息', '文件对话框 / 文件类型', '关于 · 命令行选项（帮助正文）',
         '内部调试信息（仅开发可见）']
rows.sort(key=lambda r: (ORDER.index(r['cat']) if r['cat'] in ORDER else 99, r['loc']))

keeps = [{'en': k, 'reason': v} for k, v in KEEP.items()]

json.dump({'rows': rows, 'keeps': keeps}, open(os.path.join(OUT, '对照表数据.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- HTML
from collections import Counter
cnt = Counter(r['cat'] for r in rows)
e = html.escape
parts = []
parts.append('''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>void Image Viewer 汉化对照表</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--line:#e3e6eb;--tx:#1b1f27;--dim:#667085;--acc:#0f62fe;--red:#c0392b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.6 "Microsoft YaHei","Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;margin:0 0 6px}
.sub{color:var(--dim);margin-bottom:22px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0 26px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card b{display:block;font-size:22px;color:var(--acc)}
.card span{color:var(--dim);font-size:12.5px}
.tools{display:flex;gap:10px;align-items:center;margin:0 0 14px;flex-wrap:wrap}
input[type=search]{flex:1;min-width:220px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;font-size:14px;background:var(--card)}
button{padding:9px 14px;border:1px solid var(--line);background:var(--card);border-radius:8px;cursor:pointer;font-size:13.5px}
button:hover{border-color:var(--acc);color:var(--acc)}
h2{font-size:17px;margin:30px 0 10px;padding-left:10px;border-left:4px solid var(--acc)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:13.5px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#eef1f6;font-weight:600;white-space:nowrap;position:sticky;top:0}
tr:last-child td{border-bottom:none}
td.n{color:var(--dim);width:44px;text-align:right;font-variant-numeric:tabular-nums}
td.en{font-family:Consolas,monospace;font-size:12.5px;color:#334155;white-space:pre-wrap;word-break:break-word}
td.zh{color:#0b3d91;white-space:pre-wrap;word-break:break-word}
td.loc{color:var(--dim);font-size:12.5px}
td.note{font-family:Consolas,monospace;font-size:11.5px;color:#8a94a6;white-space:nowrap}
tr.fade td{opacity:.35}
.note-box{background:#fff8e6;border:1px solid #f1d68b;border-radius:10px;padding:12px 14px;margin:22px 0;font-size:13.5px}
.note-box b{color:#8a6100}
footer{margin-top:36px;color:var(--dim);font-size:12.5px;text-align:center}
</style></head><body><div class="wrap">''')

parts.append('<h1>void Image Viewer 汉化对照表</h1>')
parts.append('<div class="sub">原程序 <code>C:\\Program Files\\voidImageViewer\\voidImageViewer.exe</code> · '
             '版本 1.0.0.13 (x64) · 有效期 原文件 MD5 <code>2c30134266aabd607e186e5252f1452f</code></div>')

parts.append('<div class="cards">')
parts.append('<div class="card"><b>%d</b><span>翻译条目合计</span></div>' % len(rows))
for c in ORDER:
    if cnt.get(c):
        parts.append('<div class="card"><b>%d</b><span>%s</span></div>' % (cnt[c], e(c)))
parts.append('<div class="card"><b>%d</b><span>保留原文（不译）</span></div>' % len(keeps))
parts.append('</div>')

parts.append('<div class="tools"><input id="q" type="search" placeholder="搜索原文 / 译文 / 界面位置…">'
             '<button onclick="clr()">清除</button></div>')

parts.append('<div class="note-box"><b>说明：</b>译文以 UTF-8 存放于程序新增的 <code>.cnstr</code> 节，'
             '并通过重定位原有的绝对指针表与 RIP-相对 LEA 指令指向新节；菜单项保留 <code>&amp;</code> 助记符，'
             '选项对话框内的命令列表按原设计剥离助记符。原始数字签名（Authenticode，10408 字节）已原样保留在文件末尾。</div>')

parts.append('''<h2>工程说明与已知限制</h2>
<ol class="notes">
<li><b>实现方式</b>：原生 Win32 x64 PE 汉化，未使用任何第三方运行库。译文统一存放于新增的
<code>.cnstr</code> 节（RVA 0x60000）；原字符串的两类引用（<code>.data</code> 中的绝对指针表 145 处、
<code>.text</code> 中的 RIP-相对 LEA 指令 54 处）全部重定位到新节；对话框文本通过重建
<code>.rsrc</code> 资源段实现（47 处）；原数字签名作为 overlay 原样搬移到文件末尾。</li>
<li><b>编码修复</b>：程序内部有 5 处内联的「逐字节 1:1 拓宽」循环（把 ANSI 字节直接当作宽字符），
原本仅适用于 ASCII。已将其重定向到新代码洞，改为先按原规则剥离 <code>&amp;</code> 助记符、
再调用程序自带的 <code>MultiByteToWideChar(CP_UTF8)</code> 转换，彻底修复「选项 → 控件」页命令列表的乱码。</li>
<li><b>已知副作用</b>：程序将 <code>%APPDATA%\\voidImageViewer\\voidImageViewer.ini</code> 中键盘快捷键的
键名由「命令显示名」派生。命令名汉化后，8 组键名（如 <code>f__keys</code>、<code>v__keys</code>）出现重名，
自定义这些命令的快捷键时会相互影响；不影响程序运行与默认快捷键。首次运行汉化版后程序会重写该 ini。</li>
<li><b>未落地 1 项</b>：<code>*.* (All Files)</code>（原 16 字节）在映像中无任何引用（属死字符串），
且中文译文 19 字节超出原长度，故未替换。</li>
<li><b>签名状态</b>：文件内容已修改，Authenticode 数字签名不再有效（签名数据仍原样保留），
程序可正常启动运行，仅在系统属性中不再显示“已验证的发布者”。</li>
</ol>''')

parts.append('''<style>
ol.notes{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 14px 14px 34px;margin:0 0 8px;font-size:13.5px}
ol.notes li{margin:7px 0}
ol.notes code{background:#eef1f6;padding:1px 5px;border-radius:4px;font-size:12.5px}
</style>''')

n = 0
for c in ORDER:
    if not cnt.get(c):
        continue
    parts.append('<h2>%s（%d 项）</h2>' % (e(c), cnt[c]))
    parts.append('<table><thead><tr><th>#</th><th>所在界面位置 / 资源标识</th><th>原文</th><th>中文译文</th><th>资源</th></tr></thead><tbody>')
    for r in rows:
        if r['cat'] != c:
            continue
        n += 1
        parts.append('<tr><td class="n">%d</td><td class="loc">%s</td><td class="en">%s</td><td class="zh">%s</td><td class="note">%s</td></tr>'
                     % (n, e(r['loc']), e(r['en']), e(r['zh']), e(r['note'])))
    parts.append('</tbody></table>')

parts.append('<h2>保留原文（不汉化）的 %d 项及原因</h2>' % len(keeps))
parts.append('<table><thead><tr><th>#</th><th>原文</th><th>保留原因</th></tr></thead><tbody>')
for i, k in enumerate(keeps, 1):
    parts.append('<tr><td class="n">%d</td><td class="en">%s</td><td class="loc">%s</td></tr>'
                 % (i, e(k['en']), e(k['reason'])))
parts.append('</tbody></table>')

parts.append('<footer>共 %d 条翻译 + %d 条保留项 · 由 WorkBuddy 自动生成</footer>' % (len(rows), len(keeps)))
parts.append('''<script>
const q=document.getElementById('q'),rows=[...document.querySelectorAll('tbody tr')];
q.addEventListener('input',()=>{const v=q.value.trim().toLowerCase();
 rows.forEach(tr=>{tr.classList.toggle('fade', v && !tr.innerText.toLowerCase().includes(v));});});
function clr(){q.value='';q.dispatchEvent(new Event('input'));}
</script></div></body></html>''')

open(os.path.join(OUT, '汉化对照表.html'), 'w', encoding='utf-8').write(''.join(parts))

from collections import Counter as C
print('对照表条目:', len(rows), dict(C(r['cat'] for r in rows)))
print('保留项:', len(keeps))
unmatched = [en for en in TR if en not in used]
print('未纳入对照表的条目:', unmatched)
