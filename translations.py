# -*- coding: utf-8 -*-
"""
Void Image Viewer 1.0.0.13 (x64) 简体中文本地化 —— 翻译表
EN = 原文（精确匹配 PE 内 ASCII/UTF-16 字符串）
ZH = 中文译文
area = 归类（用于生成对照表）
"""

# ============ 主菜单 / 菜单项（.data 菜单命令表，16 字节/项）============
MENU = [
    ("&File",              "文件(&F)"),
    ("&Open File...",      "打开文件(&O)..."),
    ("Open &Folder...",    "打开文件夹(&F)..."),
    ("Open Everything &Search...", "打开 Everything 搜索(&S)..."),
    ("&Add File...",       "添加文件(&A)..."),
    ("Add Folder...",      "添加文件夹..."),
    ("Add Everything Search...", "添加 Everything 搜索..."),
    ("Open F&ile Location...", "打开文件位置(&I)..."),
    ("&Edit...",           "编辑(&E)..."),
    ("Pre&view...",        "预览(&V)..."),
    ("&Print...",          "打印(&P)..."),
    ("Set &Desktop Wallpaper", "设为桌面壁纸(&D)"),
    ("&Close",             "关闭(&C)"),
    ("&Delete",            "删除(&D)"),
    ("Delete (Recycle)",   "删除（移入回收站）"),
    ("Delete (Permanently)", "删除（永久删除）"),
    ("&Rename",            "重命名(&M)"),
    ("P&roperties",        "属性(&R)"),
    ("E&xit",              "退出(&X)"),

    ("&Edit",              "编辑(&E)"),
    ("Cu&t",               "剪切(&T)"),
    ("&Copy",              "复制(&C)"),
    ("Copy Filename",      "复制文件名"),
    ("Cop&y Image",        "复制图像(&Y)"),
    ("&Paste",             "粘贴(&P)"),
    ("Rotate &Cloc&kwise", "顺时针旋转(&K)"),
    ("Rotate Cou&nterclockwise", "逆时针旋转(&N)"),
    ("Copy to &Folder...", "复制到文件夹(&F)..."),
    ("Mo&ve to Folder...", "移动到文件夹(&V)..."),

    ("&View",              "视图(&V)"),
    ("Caption",            "标题栏"),
    ("Frame",              "边框"),
    ("&Menu",              "菜单(&M)"),
    ("Status &Bar",        "状态栏(&B)"),
    ("&Controls",          "控件(&C)"),
    ("&Preset",            "预设(&P)"),
    ("&Minimal",           "极简(&M)"),
    ("&Compact",           "紧凑(&C)"),
    ("&Normal",            "标准(&N)"),
    ("F&ullscreen",        "全屏(&U)"),
    ("&Slideshow",         "幻灯片(&S)"),
    ("&Window Size",       "窗口大小(&W)"),
    ("50%",                "50%"),
    ("100%",               "100%"),
    ("200%",               "200%"),
    ("&Auto Fit",          "自动适应(&A)"),
    ("&Refresh",           "刷新(&R)"),
    ("&Allow Shrinking",   "允许缩小(&A)"),
    ("&Keep Aspect Ratio", "保持宽高比(&K)"),
    ("&Fill Window",       "填满窗口(&F)"),
    ("1:1",                "1:1"),
    ("&Best Fit",          "最佳适应(&B)"),
    ("Pa&n && Scan",       "平移与扫描(&N)"),
    ("&Increase Size",     "增大尺寸(&I)"),
    ("&Decrease Size",     "减小尺寸(&D)"),
    ("I&ncrease Width",    "增大宽度(&N)"),
    ("D&ecrease Width",    "减小宽度(&E)"),
    ("In&crease Height",   "增大高度(&C)"),
    ("De&cre&ase Height",  "减小高度(&G)"),
    ("&Zoom",              "缩放(&Z)"),
    ("Zoom &In",           "放大(&I)"),
    ("Zoom &Out",          "缩小(&O)"),
    ("&Reset",             "重置(&R)"),
    ("Move &Up",           "上移(&U)"),
    ("Move &Down",         "下移(&D)"),
    ("Move &Left",         "左移(&L)"),
    ("Move &Right",        "右移(&R)"),
    ("Move Up Left",       "左上移"),
    ("Move Up Right",      "右上移"),
    ("Move Down Left",     "左下移"),
    ("Move Down Right",    "右下移"),
    ("Move Cen&ter",       "居中(&T)"),
    ("Re&set",             "重置(&S)"),
    ("On &Top",            "窗口置顶(&T)"),
    ("&Always",            "总是(&A)"),
    ("&While Playing Slideshow or Animating", "播放幻灯片或动画时(&W)"),
    ("&Never",             "从不(&N)"),
    ("&Options...",        "选项(&O)..."),

    ("&Play/Pause",        "播放/暂停(&P)"),
    ("&Rate",              "速率(&R)"),
    ("&Decrease Rate",     "降低速率(&D)"),
    ("&Increase Rate",     "提高速率(&I)"),
    ("250 Milliseconds",   "250 毫秒"),
    ("500 Milliseconds",   "500 毫秒"),
    ("&1 Second",          "1 秒(&1)"),
    ("&2 Seconds",         "2 秒(&2)"),
    ("&3 Seconds",         "3 秒(&3)"),
    ("&4 Seconds",         "4 秒(&4)"),
    ("&5 Seconds",         "5 秒(&5)"),
    ("&6 Seconds",         "6 秒(&6)"),
    ("&7 Seconds",         "7 秒(&7)"),
    ("&8 Seconds",         "8 秒(&8)"),
    ("&9 Seconds",         "9 秒(&9)"),
    ("1&0 Seconds",        "10 秒(&0)"),
    ("20 Seconds",         "20 秒"),
    ("30 Seconds",         "30 秒"),
    ("40 Seconds",         "40 秒"),
    ("50 Seconds",         "50 秒"),
    ("1 Minute",           "1 分钟"),
    ("Custom...",          "自定义..."),

    ("&Animation",         "动画(&A)"),
    ("Jump &Forward",      "快进(&F)"),
    ("Jump &Backward",     "快退(&B)"),
    ("Short Jump &Forward", "短距离快进(&F)"),
    ("Short Jump &Backward", "短距离快退(&B)"),
    ("Long Jump &Forward", "长距离快进(&F)"),
    ("Long Jump &Backward", "长距离快退(&B)"),
    ("F&rame Step",        "单帧步进(&R)"),
    ("Pre&vious Frame",    "上一帧(&V)"),
    ("F&irst Frame",       "第一帧(&I)"),
    ("&Last Frame",        "最后一帧(&L)"),
    ("R&eset Rate",        "重置速率(&E)"),

    ("&Navigate",          "导航(&N)"),
    ("&Next",              "下一个(&N)"),
    ("P&revious",          "上一个(&R)"),
    ("&Home",              "第一个(&H)"),
    ("&End",               "最后一个(&E)"),
    ("S&ort",              "排序(&O)"),
    ("&Name",              "名称(&N)"),
    ("Full &Path and Filename", "完整路径和文件名(&P)"),
    ("&Size",              "大小(&S)"),
    ("Date &Modified",     "修改日期(&M)"),
    ("Date &Created",      "创建日期(&C)"),
    ("&Ascending",         "升序(&A)"),
    ("&Descending",        "降序(&D)"),
    ("&Shuffle",           "随机播放(&S)"),
    ("&Jump To...",        "跳转到(&J)..."),

    ("&Help",              "帮助(&H)"),
    ("&Command Line Options", "命令行选项(&C)"),
    ("Home &Page",         "主页(&P)"),
    ("&Donate",            "捐赠(&D)"),
    ("&About",             "关于(&A)"),
]

# ============ 选项对话框 / 属性树 / 下拉枚举 ============
OPTIONS = [
    ("General",            "常规"),
    ("View",               "视图"),
    ("Controls",           "控件"),

    ("Scroll",             "滚动"),
    ("Play/Pause Slideshow", "播放/暂停幻灯片"),
    ("Play/Pause Animation", "播放/暂停动画"),
    ("Zoom In",            "放大"),
    ("Next Image",         "下一张图像"),
    ("1:1 Scroll",         "1:1 滚动"),
    ("Move Window",        "移动窗口"),
    ("Context Menu",       "上下文菜单"),
    ("Zoom Out",           "缩小"),
    ("Previous Image",     "上一张图像"),
    ("Zoom",               "缩放"),
    ("Next/Prev",          "下一个/上一个"),
    ("Prev/Next",          "上一个/下一个"),

    ("HALFTONE (Quality)",         "HALFTONE（高质量）"),
    ("COLORONCOLOR (Performance)", "COLORONCOLOR（高性能）"),
    ("Auto Fit",           "自动适应"),

    ("Add Keyboard Shortcut",  "添加键盘快捷键"),
    ("Edit Keyboard Shortcut", "编辑键盘快捷键"),

    ("Load Everything Search", "载入 Everything 搜索"),
    ("Add Everything Search",  "添加 Everything 搜索"),
    ("Slideshow Rate",         "幻灯片速率"),
    ("Slideshow Play/Pause",   "幻灯片 播放/暂停"),
]

# ============ 状态栏 / 工具栏 / 提示 / 错误 ============
STATUS = [
    ("Loading...",             "正在加载..."),
    ("Failed to load image.",  "无法加载图像。"),
    ("File not found.",        "找不到文件。"),
    ("Slideshow playing",      "正在播放幻灯片"),
    ("PRELOAD",                "预加载"),
    ("milliseconds",           "毫秒"),
    ("seconds",                "秒"),
    ("minutes",                "分钟"),
    ("hours",                  "小时"),
    ("Actual Size",            "实际大小"),
    ("Best Fit",               "最佳适应"),
    ("Pause Slideshow",        "暂停幻灯片"),
    ("Play Slideshow",         "播放幻灯片"),
    ("POS: %d,%d RGB: %d,%d,%d", "坐标: %d,%d RGB: %d,%d,%d"),
    (" KB)",                   " KB）"),
    ("Animation rate %0.3f",   "动画速率 %0.3f"),
    ("Slideshow rate %d %S",   "幻灯片速率 %d %S"),
    ("Error %d: unable to copy %S to %S", "错误 %d：无法将 %S 复制到 %S"),
    ("Everything not available", "Everything 不可用"),
]

# ============ 文件对话框 / 文件类型 ============
FILEDLG = [
    ("Open Image",         "打开图像"),
    ("All Image Files",    "所有图像文件"),
    ("*.* (All Files)",    "*.* (所有文件)"),
    ("WebP Image",         "WebP 图像"),
    ("TIFF Image",         "TIFF 图像"),
    ("PNG Image",          "PNG 图像"),
    ("JPEG Image",         "JPEG 图像"),
    ("Icon File",          "图标文件"),
    ("Animated GIF Image", "动态 GIF 图像"),
    ("Bitmap Image",       "位图图像"),
    ("Move To",            "移动到"),
    ("Copy To",            "复制到"),
]

# ============ 关于 / 版本 / 帮助正文 ============
ABOUT = [
    ("Usage:\nvoidImageViewer.exe [/switches] [filename(s)]\n\nSwitches:\n"
     "/slideshow\tStart a slideshow.\n"
     "/fullscreen\tStart fullscreen.\n"
     "/maximized\tStart maximized.\n"
     "/window\t\tStart windowed.\n"
     "/ontop\t\tShow on top of other windows.\n"
     "/minimal\t\tBorderless window.\n"
     "/compact\t\tBordered window.\n"
     "/x <x> /y <y> /width <width> /height <height>\n"
     "\t\tSet the Window position and size.\n"
     "/rate <rate>\tSet the slideshow rate in milliseconds.\n"
     "/name\t\tSort by name.\n"
     "/path\t\tSort by full path and filename.\n"
     "/size\t\tSort by size.\n"
     "/dm\t\tSort by date modified.\n"
     "/dc\t\tSort by date created.\n"
     "/ascending\tSort in ascending order.\n"
     "/descending\tSort in descending order.\n"
     "/everything <search> Open files from an Everything search.\n"
     "/random <search>\tOpen random files from an Everything search.\n"
     "/shuffle\t\tShuffle playlist.\n"
     "/<bmp|gif|ico|jpeg|jpg|png|tif|tiff|webp>\n"
     "\t\tInstall association.\n"
     "/no<bmp|gif|ico|jpeg|jpg|png|tif|tiff|webp>\n"
     "\t\tUninstall association.\n"
     "/appdata\t\tSave settings in appdata.\n"
     "/noappdata\tSave settings in exe path.\n"
     "/startmenu\tAdd Start menu shortcuts.\n"
     "/nostartmenu\tRemove Start menu shortcuts.\n"
     "/install <path>\tInstall to the specified path.\n"
     "/install-options <...> Run with the specified options after installation.\n"
     "/uninstall <path>\tUninstall from the specified path.\n",
     "用法:\nvoidImageViewer.exe [/开关] [文件名...]\n\n开关:\n"
     "/slideshow\t启动幻灯片播放。\n"
     "/fullscreen\t启动全屏。\n"
     "/maximized\t最大化启动。\n"
     "/window\t\t以窗口方式启动。\n"
     "/ontop\t\t窗口置顶显示。\n"
     "/minimal\t\t无边框窗口。\n"
     "/compact\t\t带边框窗口。\n"
     "/x <x> /y <y> /width <宽度> /height <高度>\n"
     "\t\t设置窗口位置与尺寸。\n"
     "/rate <速率>\t设置幻灯片速率（毫秒）。\n"
     "/name\t\t按名称排序。\n"
     "/path\t\t按完整路径和文件名排序。\n"
     "/size\t\t按大小排序。\n"
     "/dm\t\t按修改日期排序。\n"
     "/dc\t\t按创建日期排序。\n"
     "/ascending\t按升序排列。\n"
     "/descending\t按降序排列。\n"
     "/everything <搜索>\t打开 Everything 搜索得到的文件。\n"
     "/random <搜索>\t从 Everything 搜索结果中随机打开文件。\n"
     "/shuffle\t\t随机播放列表。\n"
     "/<bmp|gif|ico|jpeg|jpg|png|tif|tiff|webp>\n"
     "\t\t安装文件关联。\n"
     "/no<bmp|gif|ico|jpeg|jpg|png|tif|tiff|webp>\n"
     "\t\t卸载文件关联。\n"
     "/appdata\t\t将设置保存在 appdata 中。\n"
     "/noappdata\t将设置保存在 exe 所在路径。\n"
     "/startmenu\t添加开始菜单快捷方式。\n"
     "/nostartmenu\t删除开始菜单快捷方式。\n"
     "/install <路径>\t安装到指定路径。\n"
     "/install-options <...> 安装后以指定选项运行。\n"
     "/uninstall <路径>\t从指定路径卸载。\n"),
]

# ============ 对话框资源（DIALOG）控件文本 ============
# key = 原文；值 = 译文。仅作用于 DIALOG 资源内的 title / 控件标题。
DIALOG = [
    # DIALOG 106 —— 「选项」主对话框
    ("Options - Void Image Viewer", "选项 - Void Image Viewer"),
    # DIALOG 109
    ("Set Custom Rate",     "设置自定义速率"),
    ("&Custom rate:",       "自定义速率(&C):"),
    # DIALOG 121
    ("About void Image Viewer", "关于 void Image Viewer"),
    # DIALOG 123
    ("Edit Keyboard Shortcut", "编辑键盘快捷键"),
    ("Shortcut &key:",      "快捷键(&K):"),
    ("Shortcut key currently used by:", "当前使用该快捷键的命令:"),
    # DIALOG 127
    ("Rename",              "重命名"),
    # DIALOG 128
    ("Jump To",             "跳转到"),
    # DIALOG 129
    ("Search Everything",   "搜索 Everything"),
    ("Randomize",           "随机化"),
    # DIALOG 101 —— 常规页
    ("&Store settings in %APPDATA%\\voidImageViewer", "将设置保存到 %APPDATA%\\voidImageViewer(&S)"),
    ("Allow multiple &instances", "允许多个实例(&I)"),
    ("Start &menu shortcuts", "创建开始菜单快捷方式(&M)"),
    ("Associations",        "文件关联"),
    ("Check &All",          "全选(&A)"),
    ("Check &None",         "全不选(&N)"),
    # DIALOG 107 —— 视图页
    ("&Shrink blit mode:",  "缩小时位块传输模式(&S):"),
    ("&Magnify blit mode:", "放大时位块传输模式(&M):"),
    ("Auto si&ze window:",  "自动调整窗口大小(&Z):"),
    ("&Play animations at least once in slideshow", "幻灯片中动画至少播放一次(&P)"),
    ("Preload &next image", "预加载下一张图像(&N)"),
    ("Cache &last image",   "缓存上一张图像(&L)"),
    ("&Windowed background color:", "窗口模式背景色(&W):"),
    ("&Fullscreen background color:", "全屏背景色(&F):"),
    # DIALOG 110 —— 控件页
    ("&Left click action:",  "左键单击操作(&L):"),
    ("&Right click action:", "右键单击操作(&R):"),
    ("&Mouse wheel action:", "鼠标滚轮操作(&M):"),
    ("&Commands:",           "命令(&C):"),
    ("Settings for selected command", "所选命令的设置"),
    ("&Add...",              "添加(&A)..."),
    ("&Edit...",             "编辑(&E)..."),
    ("Remo&ve",              "移除(&V)"),
    # 通用按钮
    ("OK",                   "确定"),
    ("Cancel",               "取消"),
]

# ============ 显式按 RVA 指定的附加条目（扫描器跳过者）============
EXTRA_BY_RVA = [
    (0x0443a7, ":Pos %0.3f %0.3f, Zoom %0.3f %0.3f, Aspect Ratio %0.3f",
               ":坐标 %0.3f %0.3f, 缩放 %0.3f %0.3f, 比例 %0.3f"),
]

# ============ 明确不翻译（保持原文）============
KEEP = {
    "void Image Viewer": "产品名（品牌）",
    "voidImageViewer": "产品/配置节名",
    "VOIDIMAGEVIEWER": "窗口类名",
    "unicows.dll": "依赖库文件名",
    "stobject.dll": "系统库名",
    " Uninstall.exe": "安装程序文件名",
    "Uninstall.exe": "安装程序文件名",
    "Uninstall.lnk": "快捷方式文件名",
    "void Image Viewer.lnk": "快捷方式文件名",
    "voidImageViewer.exe": "主程序文件名",
    "www.voidtools.com": "官网地址",
    "david.carpenter@voidtools.com": "作者邮箱",
    "Copyright © 2025 David Carpenter": "版权声明",
    "(x64)": "架构标识",
    "%d.%d.%d.%d%s %s": "版本号格式串",
    "Shift": "键名", "Alt": "键名", "Ctrl": "键名",
    " Preferred DropEffect": "剪贴板格式名",
    "Everything": "第三方产品名",
    "msctls_statusbar32": "系统控件类名",
    "ToolbarWindow32": "系统控件类名",
    "_VIV_REBAR": "内部窗口类名",
    "_VIV_FULLSCREEN": "内部窗口类名",
    "EVERYTHING_TASKBAR_NOTIFICATION": "内部通知消息名",
    "ext:bmp;gif;ico;jpeg;jpg;png;tif;tiff;webp <": "Everything 搜索语法",
    "*.bmp;*.gif;*.ico;*.jpeg;*.jpg;*.png;*.tif;*.tiff;*.webp": "通配符过滤器",
    "*.*": "通配符",
    "..": "路径片段", "\\*.*": "路径片段", " /": "分隔符", " - ": "分隔符",
    " | ": "分隔符", " / ": "分隔符", "- ": "分隔符", " x ": "尺寸分隔符",
    "webp": "扩展名", "tiff": "扩展名", "tif": "扩展名", "png": "扩展名",
    "jpg": "扩展名", "jpeg": "扩展名", "ico": "扩展名", "gif": "扩展名", "bmp": "扩展名",
    "&BMP": "扩展名", "&GIF": "扩展名", "IC&O": "扩展名", "JP&EG": "扩展名",
    "&JPG": "扩展名", "&PNG": "扩展名", "&TIF": "扩展名", "TIF&F": "扩展名",
    "&WEBP": "扩展名",
    "1:1": "缩放比例",
    "50%": "缩放比例", "100%": "缩放比例", "200%": "缩放比例",
    "Static": "占位静态控件（运行时被替换）",
}


def merged():
    """返回 (en -> (zh, area)) 的全量映射"""
    out = {}
    for area, tbl in (("主菜单/菜单项", MENU), ("选项设置", OPTIONS), ("状态栏/工具栏/提示", STATUS),
                      ("文件对话框/文件类型", FILEDLG), ("关于/帮助正文", ABOUT), ("对话框资源", DIALOG)):
        for en, zh in tbl:
            out[en] = (zh, area)
    for rva, en, zh in EXTRA_BY_RVA:
        out[en] = (zh, "内部调试信息")
    return out


if __name__ == '__main__':
    m = merged()
    print('翻译条目数:', len(m))
    from collections import Counter
    print(Counter(v[1] for v in m.values()))
