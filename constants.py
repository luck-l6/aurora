"""Constants and configuration data for Desktop Organizer."""

import sys
from pathlib import Path

# ── Path constants ───────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _BASE_DIR = Path(sys.executable).parent
else:
    _BASE_DIR = Path(__file__).parent

DATA_FILE = _BASE_DIR / "organizer_data.json"
CHANGELOG_FILE = _BASE_DIR / "organizer_changelog.json"
COLLECT_DIR = _BASE_DIR / "collected"
COLLECT_DIR.mkdir(exist_ok=True)

APP_VERSION = "1.3.0"

# ── Glass UI Color Palette ───────────────────────────────────────────
# 暖金色调方案 — 参考图玻璃效果：极透明薄纱感
GLASS_BG_BASE = "rgba(30,22,14,90)"         # 极透明暖棕底
GLASS_BG_MID = "rgba(40,30,18,70)"          # 中层更透
GLASS_BG_TOP = "rgba(55,40,25,50)"          # 顶层最透
GLASS_BORDER = "rgba(255,248,235,18)"       # 极淡白色边框
GLASS_BORDER_HOVER = "rgba(255,248,235,30)" # hover描边
GLASS_TEXT_PRIMARY = "rgba(255,248,235,240)" # 暖白主文字
GLASS_TEXT_SECONDARY = "rgba(196,175,120,160)" # 金色副文字
GLASS_TEXT_DIM = "rgba(196,175,120,90)"      # 暗金辅助文字
GLASS_ACCENT = "rgba(196,175,120,1.0)"      # 强调金色
GLASS_SEARCH_BG = "rgba(255,248,235,10)"    # 搜索框底
GLASS_SEARCH_BORDER = "rgba(196,175,120,25)" # 搜索框边
GLASS_SEARCH_FOCUS = "rgba(196,175,120,80)" # 搜索框聚焦
GLASS_SIDEBAR_BG = "rgba(42,31,20,160)"     # 侧栏底
GLASS_SIDEBAR_BORDER = "rgba(196,175,120,30)" # 侧栏描边
GLASS_TOOL_BG = "rgba(255,248,235,8)"       # 工具按钮底
GLASS_TOOL_HOVER = "rgba(196,175,120,30)"   # 工具按钮hover
GLASS_TOOL_ACTIVE = "rgba(196,175,120,60)"  # 工具按钮active
GLASS_SHADOW = "rgba(0,0,0,120)"            # 柔和阴影

# ── Container Style (frosted glass) ─────────────────────────────────
CONTAINER_GLASS_STYLE = """
    QFrame {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {bg_top},
            stop:0.5 {bg_mid},
            stop:1 {bg_base});
        border-radius: 24px;
        border: 1px solid {border};
    }}
""".format(
    bg_top=GLASS_BG_TOP, bg_mid=GLASS_BG_MID,
    bg_base=GLASS_BG_BASE, border=GLASS_BORDER
)

CONTAINER_TRANSPARENT_STYLE = """
    QFrame {
        background: transparent;
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,10);
    }
"""

# ── Title Style ─────────────────────────────────────────────────────
TITLE_STYLE = """
    color: {color};
    font-size: 24px;
    font-weight: bold;
    letter-spacing: 4px;
""".format(color=GLASS_TEXT_PRIMARY)

SUBTITLE_STYLE = """
    color: {color};
    font-size: 12px;
    padding-top: 4px;
""".format(color=GLASS_TEXT_SECONDARY)

# ── Search Box Style ────────────────────────────────────────────────
SEARCH_STYLE = """
    QLineEdit {{
        background: {bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 18px;
        padding-left: 18px;
        padding-right: 14px;
        font-size: 13px;
        selection-background-color: rgba(196,175,120,60);
    }}
    QLineEdit:hover {{
        border-color: {hover_border};
        background: {hover_bg};
    }}
    QLineEdit:focus {{
        border-color: {focus_border};
        background: {focus_bg};
    }}
""".format(
    bg=GLASS_SEARCH_BG, text=GLASS_TEXT_PRIMARY,
    border=GLASS_SEARCH_BORDER, hover_border=GLASS_BORDER_HOVER,
    hover_bg="rgba(255,248,235,16)", focus_border=GLASS_SEARCH_FOCUS,
    focus_bg="rgba(255,248,235,20)"
)

# ── Sidebar capsule style ───────────────────────────────────────────
SIDEBAR_STYLE = """
    QFrame {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {bg_top}, stop:1 {bg_base});
        border-radius: 22px;
        border: 1px solid {border};
    }}
""".format(
    bg_top="rgba(58,42,28,180)", bg_base=GLASS_SIDEBAR_BG,
    border=GLASS_SIDEBAR_BORDER
)

SIDEBAR_BTN_STYLE = """
    QPushButton {{
        background: transparent;
        color: {text};
        border: none;
        border-radius: 22px;
        font-size: 20px;
    }}
    QPushButton:hover {{
        background: {hover};
        color: {accent};
    }}
    QPushButton:checked {{
        background: {active};
        color: {accent};
    }}
""".format(text=GLASS_TEXT_SECONDARY, hover=GLASS_TOOL_HOVER,
           active=GLASS_TOOL_ACTIVE, accent=GLASS_ACCENT)

# ── Window Button Style ─────────────────────────────────────────────
WIN_BTN_STYLE = """
    QPushButton {{
        background: transparent;
        color: {text};
        border: none;
        border-radius: 17px;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background: {hover};
        color: {hover_text};
    }}
""".format(text=GLASS_TEXT_DIM, hover="rgba(196,175,120,25)",
           hover_text=GLASS_TEXT_PRIMARY)

WIN_CLOSE_STYLE = """
    QPushButton {{
        background: transparent;
        color: {text};
        border: none;
        border-radius: 17px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background: rgba(200,80,60,160);
        color: white;
    }}
""".format(text=GLASS_TEXT_DIM)

# ── Separator Style ─────────────────────────────────────────────────
SEPARATOR_STYLE = """
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent,
        stop:0.15 rgba(196,175,120,20),
        stop:0.5 rgba(196,175,120,40),
        stop:0.85 rgba(196,175,120,20),
        stop:1 transparent);
"""

# ── Common Styles ──────────────────────────────────────────────────────
MENU_STYLE = """
    QMenu {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(22,24,34,248), stop:1 rgba(14,16,22,248));
        color: rgba(255,255,255,220);
        border: 1px solid rgba(196,180,140,50);
        border-radius: 12px;
        padding: 6px;
    }
    QMenu::item {
        padding: 8px 28px;
        border-radius: 8px;
        margin: 1px 4px;
    }
    QMenu::item:selected {
        background: rgba(196,180,140,35);
        color: rgba(255,255,255,245);
    }
    QMenu::item:disabled {
        color: rgba(255,255,255,60);
    }
    QMenu::separator {
        height: 1px;
        background: rgba(196,180,140,25);
        margin: 4px 12px;
    }
    QMenu::indicator {
        width: 16px;
        height: 16px;
        margin-left: 6px;
    }
    QMenu::indicator:checked {
        image: none;
        background: rgba(196,180,140,180);
        border-radius: 8px;
        border: 2px solid rgba(196,180,140,230);
    }
"""

DEFAULT_DATA = {
    "categories": [
        {
            "name": "浏览器", "color": "#5CB85C",
            "items": [
                {"name": "Edge", "path": "msedge.exe"},
                {"name": "Chrome", "path": "chrome.exe"},
                {"name": "Firefox", "path": "firefox.exe"},
            ]
        },
        {
            "name": "办公工具", "color": "#4A90D9",
            "items": [
                {"name": "Word", "path": "winword.exe"},
                {"name": "Excel", "path": "excel.exe"},
                {"name": "PPT", "path": "powerpnt.exe"},
                {"name": "记事本", "path": "notepad.exe"},
            ]
        },
        {
            "name": "媒体工具", "color": "#E8A838",
            "items": [
                {"name": "音乐", "path": ""},
                {"name": "视频", "path": ""},
                {"name": "画图", "path": "mspaint.exe"},
            ]
        },
        {
            "name": "编程开发", "color": "#5BC0DE",
            "items": [
                {"name": "VSCode", "path": "code.exe"},
                {"name": "终端", "path": "wt.exe"},
            ]
        },
        {
            "name": "游戏", "color": "#34495E",
            "items": [
                {"name": "Steam", "path": "steam.exe"},
            ]
        },
        {
            "name": "更多应用", "color": "#7F8C8D",
            "items": [
                {"name": "计算器", "path": "calc.exe"},
                {"name": "截图", "path": "SnippingTool.exe"},
            ]
        },
        {
            "name": "开始菜单工具", "color": "#D4A5C9",
            "items": []
        },
    ],
    "wallpaper": {
        "type": "animated_gradient",
        "path": "",
        "color": "#1a1a2e"
    }
}

# ── Sphere skin presets ──────────────────────────────────────────
SPHERE_SKINS = {
    "default": {
        "name": "默认",
        "highlight_boost": 120,
        "saturation_boost": 0,
        "mid_alpha": 240,
        "dark_factor": 0.7,
        "shadow_factor": 0.3,
        "specular_size": 0.25,
        "specular_alpha": 160,
        "rim_alpha": 15,
        "hover_rim_alpha": 30,
        "hover_glow": True,
        "style": "glass",
    },
    "frosted": {
        "name": "磨砂",
        "highlight_boost": 50,
        "saturation_boost": -30,
        "mid_alpha": 255,
        "dark_factor": 0.65,
        "shadow_factor": 0.35,
        "specular_size": 0.45,
        "specular_alpha": 50,
        "rim_alpha": 25,
        "hover_rim_alpha": 45,
        "hover_glow": False,
        "style": "frosted",
    },
    "neon": {
        "name": "霓虹",
        "highlight_boost": 80,
        "saturation_boost": 60,
        "mid_alpha": 200,
        "dark_factor": 0.3,
        "shadow_factor": 0.1,
        "specular_size": 0.15,
        "specular_alpha": 220,
        "rim_alpha": 80,
        "hover_rim_alpha": 150,
        "hover_glow": True,
        "style": "neon",
    },
    "gem": {
        "name": "宝石",
        "highlight_boost": 150,
        "saturation_boost": 40,
        "mid_alpha": 255,
        "dark_factor": 0.55,
        "shadow_factor": 0.2,
        "specular_size": 0.12,
        "specular_alpha": 230,
        "rim_alpha": 40,
        "hover_rim_alpha": 80,
        "hover_glow": True,
        "style": "gem",
    },
    "planet": {
        "name": "星球",
        "highlight_boost": 60,
        "saturation_boost": -10,
        "mid_alpha": 255,
        "dark_factor": 0.5,
        "shadow_factor": 0.15,
        "specular_size": 0.3,
        "specular_alpha": 90,
        "rim_alpha": 20,
        "hover_rim_alpha": 35,
        "hover_glow": True,
        "style": "planet",
    },
    "water": {
        "name": "水滴",
        "highlight_boost": 100,
        "saturation_boost": -40,
        "mid_alpha": 160,
        "dark_factor": 0.8,
        "shadow_factor": 0.5,
        "specular_size": 0.35,
        "specular_alpha": 200,
        "rim_alpha": 50,
        "hover_rim_alpha": 90,
        "hover_glow": True,
        "style": "water",
    },
    "crystal": {
        "name": "水晶球",
        "highlight_boost": 160,
        "saturation_boost": -15,
        "mid_alpha": 120,
        "dark_factor": 0.80,
        "shadow_factor": 0.50,
        "specular_size": 0.15,
        "specular_alpha": 255,
        "rim_alpha": 80,
        "hover_rim_alpha": 140,
        "hover_glow": True,
        "style": "crystal",
    },
    "bubble": {
        "name": "泡泡",
        "highlight_boost": 110,
        "saturation_boost": 20,
        "mid_alpha": 80,
        "dark_factor": 0.9,
        "shadow_factor": 0.7,
        "specular_size": 0.3,
        "specular_alpha": 240,
        "rim_alpha": 90,
        "hover_rim_alpha": 140,
        "hover_glow": True,
        "style": "bubble",
    },
}
