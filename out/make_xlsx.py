# -*- coding: utf-8 -*-
"""生成《void Image Viewer 汉化对照表》Excel 版。
数据源: out/对照表数据.json  ->  {rows:[...], keeps:[...]}
输出:   out/汉化对照表.xlsx    （3 个工作表）
"""
import json
import os
from collections import OrderedDict

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "对照表数据.json")
OUT = os.path.join(HERE, "汉化对照表.xlsx")

# ---------- 视觉规范 ----------
C_TITLE_BG = "1F3864"   # 深蓝底
C_HEAD_BG = "2E5C9A"    # 表头蓝
C_HEAD_FG = "FFFFFF"
C_BAND = "EEF3FA"       # 分类分隔浅蓝
C_CAT_FG = "1F3864"
C_LINE = "BFCCDD"

FONT = "微软雅黑"
FN = "等线"

thin = Side(style="thin", color=C_LINE)
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def style_header(ws, row, ncol, height=26):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = PatternFill("solid", fgColor=C_HEAD_BG)
        cell.font = Font(name=FONT, size=10.5, bold=True, color=C_HEAD_FG)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = height


def sheet_main(wb, rows):
    ws = wb.create_sheet("汉化对照表")
    headers = ["序号", "分类", "所在界面位置 / 资源标识", "原文（English）", "中文译文"]
    widths = [7, 26, 34, 42, 46]

    # 分类保持原始出现顺序
    cats = OrderedDict()
    for r in rows:
        cats.setdefault(r["cat"], []).append(r)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    t = ws.cell(row=1, column=1)
    t.value = "void Image Viewer  中文本地化对照表"
    t.fill = PatternFill("solid", fgColor=C_TITLE_BG)
    t.font = Font(name=FONT, size=13, bold=True, color="FFFFFF")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 34

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
    s = ws.cell(row=2, column=1)
    s.value = "共 %d 条界面文本　|　程序：C:\\Program Files\\voidImageViewer\\voidImageViewer.exe（x64 原生 PE）　|　另有 %d 条保留原文项见「保留原文」表" % (len(rows), len(_KEEPS))
    s.font = Font(name=FN, size=9.5, color="4A5568")
    s.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20

    r = 3
    for c, h in enumerate(headers, 1):
        ws.cell(row=r, column=c, value=h)
    style_header(ws, r, len(headers))
    ws.freeze_panes = "A4"
    r += 1

    idx = 0
    for cat, items in cats.items():
        # 分类分隔行
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(headers))
        cc = ws.cell(row=r, column=1)
        cc.value = "◆  %s　（%d 条）" % (cat, len(items))
        cc.fill = PatternFill("solid", fgColor=C_BAND)
        cc.font = Font(name=FONT, size=10, bold=True, color=C_CAT_FG)
        cc.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).border = BORDER
        ws.row_dimensions[r].height = 22
        r += 1
        for it in items:
            idx += 1
            vals = [idx, it["cat"], it.get("loc", ""), it.get("en", ""), it.get("zh", "")]
            for c, v in enumerate(vals, 1):
                cell = ws.cell(row=r, column=c, value=v)
                cell.border = BORDER
                cell.font = Font(name=FN, size=10)
                if c in (1, 2):
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                if c == 4:
                    cell.font = Font(name="Consolas", size=10, color="334155")
                if c == 5:
                    cell.font = Font(name=FN, size=10, bold=True, color="1F3864")
            # 长文本行高上限（列宽约 42/46 字符，按 44 字符/行估算，最多 6 行）
            est = max(len(str(it.get("en", ""))) / 40.0, len(str(it.get("zh", ""))) / 44.0)
            lines = max(1, min(6, int(est) + (1 if est % 1 else 0)))
            if lines > 1:
                ws.row_dimensions[r].height = 15.5 * lines
            r += 1

    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_view.showGridLines = False
    ws.auto_filter.ref = "A3:%s%d" % (get_column_letter(len(headers)), r - 1)
    return ws, idx


def sheet_keeps(wb, keeps):
    ws = wb.create_sheet("保留原文")
    headers = ["序号", "原文（English）", "保留原因"]
    widths = [7, 52, 46]

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    t = ws.cell(row=1, column=1)
    t.value = "保留原文（不翻译）"
    t.fill = PatternFill("solid", fgColor=C_TITLE_BG)
    t.font = Font(name=FONT, size=13, bold=True, color="FFFFFF")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 34

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
    s = ws.cell(row=2, column=1)
    s.value = "以下 %d 项为品牌名、格式占位符（%%s/%%d）、单位符号、正则/技术标识等，翻译后会破坏功能或引起误解，故保留原文" % len(keeps)
    s.font = Font(name=FN, size=9.5, color="4A5568")
    s.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 20

    r = 3
    for c, h in enumerate(headers, 1):
        ws.cell(row=r, column=c, value=h)
    style_header(ws, r, len(headers))
    ws.freeze_panes = "A4"
    r += 1
    for i, k in enumerate(keeps, 1):
        vals = [i, k.get("en", ""), k.get("reason", "")]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = BORDER
            if c == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = Font(name=FN, size=10)
            elif c == 2:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                cell.font = Font(name="Consolas", size=10, color="334155")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                cell.font = Font(name=FN, size=10, color="1F3864")
        r += 1

    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_view.showGridLines = False
    ws.auto_filter.ref = "A3:C%d" % (r - 1)
    return ws


NOTES = [
    ("工程说明与已知限制", ""),
    ("", ""),
    ("目标程序", "C:\\Program Files\\voidImageViewer\\voidImageViewer.exe"),
    ("程序类型", "x64 原生 Win32 PE（非 Qt / 非 Electron / 非 .NET）"),
    ("汉化方式", "新增 .cnstr 节（RVA 0x60000）存放 UTF-8 中文译文，改写引用重定位"),
    ("覆盖范围", "菜单、菜单项、选项对话框（含下拉列表 / 列表项）、对话框资源（DIALOG）、状态栏 / 工具栏提示 / 错误信息、文件对话框与文件类型、关于页帮助正文"),
    ("译文总量", "223 条界面文本 + 59 条保留原文项"),
    ("", ""),
    ("术语一致性", "Open / Close / Save / Zoom 等统一译为「打开 / 关闭 / 保存 / 缩放」；File / Edit / View / Image / Tools / Help 统一译为「文件 / 编辑 / 视图 / 图像 / 工具 / 帮助」"),
    ("", ""),
    ("已知限制 1", "「控件」页的命令列表乱码问题已修复：程序内部 5 处内联逐字节 1:1 拓宽循环被重定向到新增代码洞，改用 MultiByteToWideChar(CP_UTF8) 转换。"),
    ("已知限制 2", "「*.* (All Files)」文件类型项（原映像 RVA 0x044819）在原程序内无任何引用，且中文译文超长会溢出，未落地替换。"),
    ("已知限制 3", "快捷键配置项副作用：程序会把快捷键配置写入 %APPDATA%\\voidImageViewer\\voidImageViewer.ini，键名由命令名派生；汉化后 8 组键名出现同名，但快捷键取值完全一致，无设置丢失。已随本次交付恢复原始配置。"),
    ("", ""),
    ("原版备份", "backup\\voidImageViewer.exe.installed-before-cn"),
    ("配置备份", "backup\\voidImageViewer.ini.roaming.bak"),
    ("汉化二进制", "out\\voidImageViewer.cn.exe（383,144 字节）"),
]


def sheet_notes(wb):
    ws = wb.create_sheet("工程说明")
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 96

    ws.merge_cells("A1:B1")
    t = ws["A1"]
    t.value = "工程说明与已知限制"
    t.fill = PatternFill("solid", fgColor=C_TITLE_BG)
    t.font = Font(name=FONT, size=13, bold=True, color="FFFFFF")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 34

    r = 3
    for k, v in NOTES:
        if not k and not v:
            r += 1
            continue
        a = ws.cell(row=r, column=1, value=k)
        a.font = Font(name=FONT, size=10, bold=True, color=C_CAT_FG)
        a.alignment = Alignment(horizontal="left", vertical="top")
        b = ws.cell(row=r, column=2, value=v)
        b.font = Font(name=FN, size=10)
        b.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        if len(v) > 95:
            ws.row_dimensions[r].height = 15 * (len(v) // 95 + 1)
        r += 1
    ws.sheet_view.showGridLines = False
    return ws


_KEEPS = []


def main():
    global _KEEPS
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)
    rows = d["rows"]
    keeps = d["keeps"]
    _KEEPS = keeps

    wb = Workbook()
    wb.remove(wb.active)
    _, n = sheet_main(wb, rows)
    sheet_keeps(wb, keeps)
    sheet_notes(wb)
    wb.save(OUT)
    print("OK rows=%d keeps=%d -> %s" % (n, len(keeps), OUT))


if __name__ == "__main__":
    main()
