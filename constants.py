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

APP_VERSION = "1.2.0"

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
