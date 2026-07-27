"""
桌面收纳 - Desktop Organizer
A modern desktop organizer with radial menu design.
Click a category circle to see apps arranged around it.
"""

import sys
import json
import os
import shutil
import math
import ctypes
import struct
import time
import tempfile
import random
import winreg
from ctypes import wintypes
from pathlib import Path

import PyQt5
_pyqt5_dir = os.path.dirname(PyQt5.__file__)
_plugins_path = os.path.join(_pyqt5_dir, "Qt5", "plugins")
if os.path.isdir(_plugins_path):
    os.environ["QT_PLUGIN_PATH"] = _plugins_path
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(_plugins_path, "platforms")
_bin_path = os.path.join(_pyqt5_dir, "Qt5", "bin")
if os.path.isdir(_bin_path) and _bin_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _bin_path + os.pathsep + os.environ.get("PATH", "")

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMenu,
    QInputDialog, QColorDialog, QMessageBox, QLineEdit,
    QGraphicsDropShadowEffect, QDialog, QSlider, QComboBox,
    QFormLayout, QDialogButtonBox, QScrollArea, QSystemTrayIcon, QAction,
    QTextEdit, QTabWidget, QRadioButton, QButtonGroup, QGroupBox,
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import (
    Qt, QPoint, QSize, pyqtSignal, QRectF, QTimer
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QCursor, QPainterPath, QBrush, QPen,
    QPixmap, QImage, QImageReader, QRadialGradient, QLinearGradient, QIcon
)

from wallpaper_engine import WallpaperManager

if getattr(sys, 'frozen', False):
    _BASE_DIR = Path(sys.executable).parent
else:
    _BASE_DIR = Path(__file__).parent
DATA_FILE = _BASE_DIR / "organizer_data.json"
CHANGELOG_FILE = _BASE_DIR / "organizer_changelog.json"
COLLECT_DIR = _BASE_DIR / "collected"
COLLECT_DIR.mkdir(exist_ok=True)

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

APP_VERSION = "1.2.0"

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


def _move_to_collect(src):
    """Move a file/folder to the collected directory."""
    name = os.path.basename(src)
    dst = COLLECT_DIR / name
    if dst.exists():
        base, ext = os.path.splitext(name)
        i = 1
        while dst.exists():
            dst = COLLECT_DIR / f"{base}_{i}{ext}"
            i += 1
    shutil.move(str(src), str(dst))
    return str(dst)


# ─── Windows Icon Extractor ─────────────────────────────────────────

class SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", ctypes.c_void_p),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", ctypes.c_uint),
        ("szDisplayName", ctypes.c_wchar * 260),
        ("szTypeName", ctypes.c_wchar * 80),
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

_shell32 = ctypes.windll.shell32
_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32

_user32.GetDC.restype = ctypes.c_void_p
_user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_user32.DestroyIcon.argtypes = [ctypes.c_void_p]
_user32.DestroyIcon.restype = wintypes.BOOL
_user32.DrawIconEx.argtypes = [
    ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
    ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint
]
_user32.DrawIconEx.restype = wintypes.BOOL
_gdi32.CreateDIBSection.restype = ctypes.c_void_p
_gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
_gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_gdi32.SelectObject.restype = ctypes.c_void_p
_gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
_gdi32.DeleteObject.restype = wintypes.BOOL
_gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
_gdi32.DeleteDC.restype = wintypes.BOOL

SHGFI_ICON = 0x000000100
_icon_cache = {}  # (path, size) -> QPixmap, max 200 entries
_ICON_CACHE_MAX = 200
_icon_cache_order = []  # LRU order: oldest first


def _to_storage_path(abs_path):
    """Convert absolute path to relative if under _BASE_DIR, else keep absolute."""
    if not abs_path:
        return ""
    try:
        rel = os.path.relpath(abs_path, str(_BASE_DIR))
        if not rel.startswith(".."):
            return rel
    except (ValueError, OSError):
        pass
    return abs_path


def _resolve_path(path):
    if not path:
        return ""
    if os.path.isabs(path) and os.path.exists(path):
        return path
    # Resolve relative paths against _BASE_DIR
    if not os.path.isabs(path):
        full = os.path.normpath(_BASE_DIR / path)
        if os.path.exists(full):
            return full
    for p in os.environ.get("PATH", "").split(os.pathsep):
        full = os.path.join(p.strip(), path)
        if os.path.exists(full):
            return full
    search_dirs = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", ""),
        r"C:\Windows", r"C:\Windows\System32",
    ]
    for d in search_dirs:
        if not d:
            continue
        full = os.path.join(d, path)
        if os.path.exists(full):
            return full
        try:
            for entry in os.listdir(d):
                full = os.path.join(d, entry, path)
                if os.path.exists(full):
                    return full
        except (PermissionError, FileNotFoundError):
            pass
    return path


def _extract_icon_pixmap(path, size=48):
    global _icon_cache_order
    if not path:
        return None
    cache_key = (path, size)
    if cache_key in _icon_cache:
        # Move to end (most recently used)
        if cache_key in _icon_cache_order:
            _icon_cache_order.remove(cache_key)
        _icon_cache_order.append(cache_key)
        return _icon_cache[cache_key]
    resolved = _resolve_path(path)
    if not resolved or not os.path.exists(resolved):
        return None

    sfi = SHFILEINFO()
    hr = _shell32.SHGetFileInfoW(resolved, 0, ctypes.byref(sfi), ctypes.sizeof(sfi), SHGFI_ICON)
    if hr == 0 or not sfi.hIcon:
        return None

    pixmap = _hicon_to_qpixmap(sfi.hIcon, size)
    _user32.DestroyIcon(sfi.hIcon)
    if pixmap and not pixmap.isNull():
        # Evict oldest entry if cache is full
        while len(_icon_cache) >= _ICON_CACHE_MAX and _icon_cache_order:
            old_key = _icon_cache_order.pop(0)
            _icon_cache.pop(old_key, None)
        _icon_cache[cache_key] = pixmap
        _icon_cache_order.append(cache_key)
        return pixmap
    return None


def _clear_icon_cache_for(path):
    """Remove cached icon for a specific path (call when item is deleted)."""
    global _icon_cache_order
    keys_to_remove = [k for k in _icon_cache if k[0] == path]
    for k in keys_to_remove:
        _icon_cache.pop(k, None)
        if k in _icon_cache_order:
            _icon_cache_order.remove(k)


def _hicon_to_qpixmap(hicon, target_size):
    size = target_size or 48
    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = size
    bmi.bmiHeader.biHeight = -size
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    bits = ctypes.c_void_p()
    hbitmap = _gdi32.CreateDIBSection(0, ctypes.byref(bmi), 0, ctypes.byref(bits), 0, 0)
    if not hbitmap:
        return None

    hdc_screen = _user32.GetDC(0)
    hdc_mem = _gdi32.CreateCompatibleDC(hdc_screen)
    old_bmp = _gdi32.SelectObject(hdc_mem, hbitmap)
    _user32.DrawIconEx(hdc_mem, 0, 0, hicon, size, size, 0, 0, 3)

    buf = (ctypes.c_byte * (size * size * 4))()
    ctypes.memmove(buf, bits, size * size * 4)

    _gdi32.SelectObject(hdc_mem, old_bmp)
    _gdi32.DeleteObject(hbitmap)
    _gdi32.DeleteDC(hdc_mem)
    _user32.ReleaseDC(0, hdc_screen)

    img_data = bytearray(size * size * 4)
    has_pixels = False
    for y in range(size):
        for x in range(size):
            idx = (y * size + x) * 4
            b, g, r, a = buf[idx]&0xFF, buf[idx+1]&0xFF, buf[idx+2]&0xFF, buf[idx+3]&0xFF
            if r or g or b or a:
                has_pixels = True
            if a == 0 and (r or g or b):
                a = 255
            img_data[idx], img_data[idx+1], img_data[idx+2], img_data[idx+3] = b, g, r, a

    if not has_pixels:
        return None
    return QPixmap.fromImage(QImage(bytes(img_data), size, size, QImage.Format_ARGB32))


def _load_image_as_pixmap(path, size=48):
    if not path or not os.path.exists(path):
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.ico', '.webp'}:
        return None
    reader = QImageReader(path)
    reader.setScaledSize(QSize(size, size))
    img = reader.read()
    return None if img.isNull() else QPixmap.fromImage(img)


def get_icon_pixmap(path, size=48):
    if not path:
        return None
    cache_key = (path, size)
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]
    pixmap = _load_image_as_pixmap(path, size)
    if pixmap and not pixmap.isNull():
        _icon_cache[cache_key] = pixmap
        return pixmap
    return _extract_icon_pixmap(path, size)


# ─── App Circle Button (used in radial menu) ────────────────────────

class AppButton(QPushButton):
    """Small 3D sphere button showing an app icon, used inside RadialMenu."""
    rightClicked = pyqtSignal()

    def __init__(self, name, color, icon_path="", parent=None):
        super().__init__(parent)
        self.app_name = name
        self.base_color = QColor(color)
        self.setFixedSize(140, 140)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._anim_opacity = 1.0  # animation opacity, painted directly
        self._anim_scale = 1.0    # animation scale, 0~1
        self._icon_pixmap = get_icon_pixmap(icon_path, 80) if icon_path else None
        if not self._icon_pixmap:
            label = name[:2] if len(name) >= 2 else name
            self.setText(label)
        self._cached_sphere = None  # cached pixmap
        self._cached_hover = None

    def _get_skin(self):
        skin_key = getattr(CategoryCircleButton, 'current_skin', 'default') or 'default'
        if skin_key.startswith("custom:") and hasattr(CategoryCircleButton, '_custom_skin_data'):
            return CategoryCircleButton._custom_skin_data or SPHERE_SKINS["default"]
        return SPHERE_SKINS.get(skin_key, SPHERE_SKINS["default"])

    def _render_cache(self):
        """Pre-render sphere body to pixmap for fast painting (simplified for speed)."""
        w, h = self.width(), self.height()
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing, True)
        c = self.base_color
        r = min(w, h) / 2.0

        # Simplified gradient - single radial gradient for speed
        grad = QRadialGradient(w * 0.4, h * 0.35, r * 0.8, w * 0.5, h * 0.5, r)
        hh, ss, vv, _ = c.getHsv()
        # Bright highlight
        grad.setColorAt(0.0, QColor.fromHsv(hh, min(255, ss + 20), min(255, vv + 60), 255))
        # Mid tone
        grad.setColorAt(0.4, c)
        # Dark edge
        grad.setColorAt(0.85, QColor.fromHsv(hh, ss, max(0, int(vv * 0.4)), 240))
        # Shadow
        grad.setColorAt(1.0, QColor.fromHsv(hh, ss, max(0, int(vv * 0.15)), 200))

        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, w - 4, h - 4)

        # Simple rim highlight
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(4, 4, w - 8, h - 8)

        # Icon or text on top
        if self._icon_pixmap:
            p.save()
            clip = QPainterPath()
            clip.addEllipse(4, 4, w - 8, h - 8)
            p.setClipPath(clip)
            ix = (w - self._icon_pixmap.width()) // 2
            iy = (h - self._icon_pixmap.height()) // 2 - 10
            p.drawPixmap(ix, iy, self._icon_pixmap)
            p.restore()
            # App name below icon
            p.setPen(QColor(255, 255, 255, 200))
            p.setFont(QFont("Microsoft YaHei", max(7, w // 12), QFont.Bold))
            p.drawText(QRectF(0, h * 0.58, w, h * 0.35), Qt.AlignHCenter | Qt.AlignTop, self.app_name)
        else:
            # Text only - larger font
            p.setPen(QColor(255, 255, 255, 220))
            p.setFont(QFont("Microsoft YaHei", max(7, w // 8), QFont.Bold))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self.app_name)

        p.end()
        self._cached_sphere = pixmap

        # Hover glow overlay
        glow = QPixmap(w, h)
        glow.fill(Qt.transparent)
        gp = QPainter(glow)
        gp.setRenderHint(QPainter.Antialiasing, True)
        g = QRadialGradient(w / 2, h / 2, r + 4, w / 2, h / 2, r)
        g.setColorAt(0.85, QColor(255, 255, 255, 0))
        g.setColorAt(0.95, QColor(255, 255, 255, 30))
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        gp.setBrush(g)
        gp.setPen(Qt.NoPen)
        gp.drawEllipse(-2, -2, w + 4, h + 4)
        gp.setPen(QPen(QColor(255, 255, 255, 25), 1.2))
        gp.setBrush(Qt.NoBrush)
        gp.drawEllipse(2, 2, w - 4, h - 4)
        gp.end()
        self._cached_hover = glow

    def paintEvent(self, event):
        try:
            if not self._cached_sphere:
                self._render_cache()
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.setOpacity(self._anim_opacity)
            s = self._anim_scale
            if s != 1.0:
                cx, cy = self.width() / 2, self.height() / 2
                painter.translate(cx, cy)
                painter.scale(s, s)
                painter.translate(-cx, -cy)
            painter.drawPixmap(0, 0, self._cached_sphere)
            if self._hover and self._cached_hover:
                painter.drawPixmap(0, 0, self._cached_hover)
            painter.end()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("AppButton paintEvent failed: %s", exc)

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def contextMenuEvent(self, e):
        self.rightClicked.emit()
        e.accept()


# ─── Category Circle Button ─────────────────────────────────────────

class CategoryCircleButton(QPushButton):
    """A circular button representing a category, shown on the main grid."""
    menuRequested = pyqtSignal(object)  # emits self for context menu
    current_skin = "default"  # class-level skin key

    def __init__(self, category_data, parent=None):
        super().__init__(parent)
        self.category_data = category_data
        self.setFixedSize(160, 160)
        self._hover = False
        # Elastic follow offset (applied to rendered position)
        self.hover_ox = 0.0
        self.hover_oy = 0.0
        self._target_ox = 0.0
        self._target_oy = 0.0
        # Pixmap cache — parent _CircleArea.paintEvent draws this
        self._cached_pixmap = None
        self._cached_hover_state = False
        self._cached_skin_key = None
        self._cached_color = None
        self._setup()

    def _setup(self):
        name = self.category_data["name"]
        color = self.category_data.get("color", "#4A90D9")
        items = self.category_data.get("items", [])

    @staticmethod
    def _adj_color(c, boost=0, sat_boost=0, factor=1.0, alpha=255):
        """Adjust a QColor with brightness boost, saturation boost, and factor."""
        h, s, v, a = c.getHsv()
        s = min(255, max(0, s + sat_boost))
        v = min(255, max(0, int(v * factor)))
        nc = QColor.fromHsv(h, s, v, alpha)
        if boost:
            nc = QColor(min(255, nc.red() + boost),
                        min(255, nc.green() + boost),
                        min(255, nc.blue() + boost), alpha)
        return nc

    def _is_cache_valid(self):
        """Check if the cached pixmap is still valid."""
        skin_key = self.current_skin
        if skin_key.startswith("custom:"):
            skin_key = "custom"
        color_val = self.category_data.get("color", "#4A90D9")
        return (self._cached_pixmap is not None
                and self._cached_hover_state == self._hover
                and self._cached_skin_key == skin_key
                and self._cached_color == color_val)

    def _render_to_cache(self, size=160):
        """Render the full sphere to a cached pixmap at fixed size."""
        w, h = size, size
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        c = QColor(self.category_data.get("color", "#4A90D9"))
        r = min(w, h) / 2
        if self.current_skin.startswith("custom:") and hasattr(self, '_custom_skin_data'):
            skin = self._custom_skin_data
        else:
            skin = SPHERE_SKINS.get(self.current_skin, SPHERE_SKINS["default"])
        st = skin["style"]
        ac = self._adj_color  # shortcut

        # ── Drop shadow ──
        shadow_grad = QRadialGradient(w / 2 + 2, h / 2 + 4, r + 2,
                                       w / 2 + 2, h / 2 + 4)
        shadow_alpha = 80 if st in ("neon", "gem") else 60
        shadow_grad.setColorAt(0.7, QColor(0, 0, 0, shadow_alpha))
        shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawEllipse(0, 0, w, h)
        painter.fillRect(0, 0, w, h, QBrush(shadow_grad))

        light_x = w * 0.35
        light_y = h * 0.3

        if st == "neon":
            # ── NEON: dark center, glowing ring ──
            # Dark inner sphere
            dark = ac(c, boost=0, sat_boost=skin["saturation_boost"],
                      factor=0.15, alpha=skin["mid_alpha"])
            inner_grad = QRadialGradient(w / 2, h / 2, r * 0.85, w / 2, h / 2, r)
            inner_grad.setColorAt(0.0, QColor(0, 0, 0, 180))
            inner_grad.setColorAt(0.7, dark)
            inner_grad.setColorAt(1.0, ac(c, boost=skin["highlight_boost"],
                                          sat_boost=skin["saturation_boost"],
                                          factor=0.5, alpha=200))
            painter.setBrush(inner_grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Glow ring
            for i in range(3):
                a_val = skin["hover_rim_alpha"] if self._hover else skin["rim_alpha"]
                a_val = a_val - i * 20
                if a_val <= 0:
                    break
                pen_w = 3.5 - i * 0.8
                painter.setPen(QPen(ac(c, boost=skin["highlight_boost"],
                                       sat_boost=skin["saturation_boost"],
                                       alpha=a_val), pen_w))
                painter.setBrush(Qt.NoBrush)
                off = 2 + i * 2
                painter.drawEllipse(off, off, w - off * 2, h - off * 2)

        elif st == "gem":
            # ── GEM: sharp bright highlights, saturated ──
            # Main body with sharp transitions
            sphere_grad = QRadialGradient(light_x, light_y, r * 0.9,
                                           w / 2 + r * 0.2, h / 2 + r * 0.25)
            sphere_grad.setColorAt(0.0, ac(c, boost=skin["highlight_boost"],
                                           sat_boost=skin["saturation_boost"],
                                           alpha=255))
            sphere_grad.setColorAt(0.2, ac(c, boost=80,
                                           sat_boost=skin["saturation_boost"],
                                           alpha=255))
            sphere_grad.setColorAt(0.3, ac(c, boost=0,
                                           sat_boost=skin["saturation_boost"],
                                           alpha=skin["mid_alpha"]))
            sphere_grad.setColorAt(0.6, ac(c, boost=0,
                                           sat_boost=skin["saturation_boost"],
                                           factor=skin["dark_factor"], alpha=240))
            sphere_grad.setColorAt(0.85, ac(c, factor=skin["shadow_factor"],
                                            alpha=230))
            sphere_grad.setColorAt(1.0, ac(c, factor=0.1, alpha=220))
            painter.setBrush(sphere_grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Sharp specular (star-like)
            spec_grad = QRadialGradient(light_x - 3, light_y - 5, r * skin["specular_size"],
                                         light_x - 3, light_y - 5)
            spec_grad.setColorAt(0.0, QColor(255, 255, 255, skin["specular_alpha"]))
            spec_grad.setColorAt(0.3, QColor(255, 255, 255, 60))
            spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(spec_grad)
            painter.drawEllipse(2, 2, w - 4, h - 4)

        elif st == "planet":
            # ── PLANET: with ring and surface bands ──
            sphere_grad = QRadialGradient(light_x, light_y, r * 1.1,
                                           w / 2 + r * 0.15, h / 2 + r * 0.2)
            sphere_grad.setColorAt(0.0, ac(c, boost=skin["highlight_boost"],
                                           sat_boost=skin["saturation_boost"],
                                           alpha=255))
            sphere_grad.setColorAt(0.3, ac(c, sat_boost=skin["saturation_boost"],
                                           alpha=skin["mid_alpha"]))
            sphere_grad.setColorAt(0.6, ac(c, sat_boost=skin["saturation_boost"],
                                           factor=skin["dark_factor"], alpha=245))
            sphere_grad.setColorAt(1.0, ac(c, factor=skin["shadow_factor"],
                                           alpha=220))
            painter.setBrush(sphere_grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Surface bands (horizontal lines)
            painter.save()
            clip_path = QPainterPath()
            clip_path.addEllipse(2, 2, w - 4, h - 4)
            painter.setClipPath(clip_path)
            for i in range(3):
                by = h * 0.3 + i * h * 0.15
                painter.setPen(QPen(ac(c, boost=20, alpha=40), 2))
                painter.drawLine(int(w * 0.15), int(by), int(w * 0.85), int(by))
            painter.restore()
            # Ring around planet
            painter.save()
            painter.setPen(QPen(ac(c, boost=skin["highlight_boost"],
                                   sat_boost=skin["saturation_boost"],
                                   alpha=skin["rim_alpha"] + 15), 2.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(int(w * 0.05), int(h * 0.35),
                                int(w * 0.9), int(h * 0.3))
            painter.restore()
            # Specular
            spec_grad = QRadialGradient(light_x - 4, light_y - 6, r * skin["specular_size"],
                                         light_x - 4, light_y - 6)
            spec_grad.setColorAt(0.0, QColor(255, 255, 255, skin["specular_alpha"]))
            spec_grad.setColorAt(0.5, QColor(255, 255, 255, 30))
            spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(spec_grad)
            painter.drawEllipse(2, 2, w - 4, h - 4)

        elif st == "water":
            # ── WATER DROP: translucent with refraction bright spots ──
            sphere_grad = QRadialGradient(w / 2, h / 2, r * 0.2, w / 2, h / 2, r)
            sphere_grad.setColorAt(0.0, QColor(255, 255, 255, 120))
            sphere_grad.setColorAt(0.15, ac(c, boost=skin["highlight_boost"],
                                            sat_boost=skin["saturation_boost"],
                                            alpha=100))
            sphere_grad.setColorAt(0.5, ac(c, sat_boost=skin["saturation_boost"],
                                           factor=skin["dark_factor"],
                                           alpha=skin["mid_alpha"]))
            sphere_grad.setColorAt(0.85, ac(c, factor=skin["shadow_factor"],
                                            alpha=140))
            sphere_grad.setColorAt(1.0, ac(c, factor=0.2, alpha=60))
            painter.setBrush(sphere_grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Refraction bright spots
            for sx, sy, sa in [(0.3, 0.25, 180), (0.6, 0.55, 90), (0.45, 0.7, 60)]:
                sg = QRadialGradient(w * sx, h * sy, r * 0.12, w * sx, h * sy)
                sg.setColorAt(0.0, QColor(255, 255, 255, sa))
                sg.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(sg)
                painter.drawEllipse(2, 2, w - 4, h - 4)
            # Rim
            painter.setPen(QPen(QColor(255, 255, 255,
                            skin["hover_rim_alpha"] if self._hover else skin["rim_alpha"]), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(3, 3, w - 6, h - 6)

        elif st == "crystal":
            # ── CRYSTAL BALL: ultra-real glass sphere ──
            # Inspired by real crystal ball photos: multiple sharp specular
            # hotspots, rim light, deep translucency, scattered sparkle dots.
            painter.save()
            clip = QPainterPath()
            clip.addEllipse(2, 2, w - 4, h - 4)
            painter.setClipPath(clip)

            # Layer 1: Deep body — radial gradient simulating glass depth
            body = QRadialGradient(w * 0.50, h * 0.42, r * 0.15, w * 0.50, h * 0.50, r)
            body.setColorAt(0.00, QColor(255, 255, 255, 230))
            body.setColorAt(0.05, ac(c, boost=100, sat_boost=30, alpha=255))
            body.setColorAt(0.15, ac(c, boost=60, sat_boost=20, alpha=252))
            body.setColorAt(0.30, ac(c, boost=10, sat_boost=5, alpha=245))
            body.setColorAt(0.50, ac(c, factor=0.55, alpha=235))
            body.setColorAt(0.70, ac(c, factor=0.30, alpha=220))
            body.setColorAt(0.85, ac(c, factor=0.15, alpha=200))
            body.setColorAt(1.00, ac(c, factor=0.06, alpha=170))
            painter.setBrush(body)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            # Layer 2: Inner refraction glow — warm tinted light inside
            refract = QRadialGradient(w * 0.55, h * 0.55, r * 0.08,
                                      w * 0.50, h * 0.50, r * 0.45)
            refract.setColorAt(0.0, ac(c, boost=140, alpha=60))
            refract.setColorAt(0.3, ac(c, boost=80, alpha=30))
            refract.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(refract)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            # Layer 3: Primary specular — sharp bright highlight (top-left)
            spec1 = QRadialGradient(w * 0.38, h * 0.22, r * 0.03,
                                    w * 0.38, h * 0.22, r * 0.28)
            spec1.setColorAt(0.0, QColor(255, 255, 255, 255))
            spec1.setColorAt(0.05, QColor(255, 255, 255, 240))
            spec1.setColorAt(0.15, QColor(255, 255, 255, 140))
            spec1.setColorAt(0.35, QColor(255, 255, 255, 40))
            spec1.setColorAt(0.60, QColor(255, 255, 255, 0))
            painter.setBrush(spec1)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            # Layer 4: Secondary specular — smaller reflection (right side)
            spec2 = QRadialGradient(w * 0.62, h * 0.30, r * 0.015,
                                    w * 0.62, h * 0.30, r * 0.12)
            spec2.setColorAt(0.0, QColor(255, 255, 255, 200))
            spec2.setColorAt(0.15, QColor(255, 255, 255, 100))
            spec2.setColorAt(0.50, QColor(255, 255, 255, 20))
            spec2.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(spec2)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            # Layer 5: Scattered sparkle dots (like real glass reflections)
            sparkles = [
                (0.30, 0.35, 0.012, 180),
                (0.55, 0.18, 0.010, 150),
                (0.72, 0.42, 0.015, 130),
                (0.42, 0.50, 0.008, 110),
                (0.25, 0.55, 0.010, 90),
                (0.65, 0.58, 0.009, 80),
            ]
            for sx, sy, sr, sa in sparkles:
                sp = QRadialGradient(w * sx, h * sy, r * sr * 0.3,
                                     w * sx, h * sy, r * sr)
                sp.setColorAt(0.0, QColor(255, 255, 255, sa))
                sp.setColorAt(0.4, QColor(255, 255, 255, sa // 3))
                sp.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(sp)
                painter.drawEllipse(2, 2, w - 4, h - 4)

            # Layer 6: Rim light — bright edge catching light from behind
            rim_grad = QRadialGradient(w * 0.50, h * 0.50, r * 0.75,
                                       w * 0.50, h * 0.50, r)
            rim_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            rim_grad.setColorAt(0.70, QColor(255, 255, 255, 0))
            rim_grad.setColorAt(0.88, QColor(255, 255, 255, 45))
            rim_grad.setColorAt(0.95, QColor(255, 255, 255, 25))
            rim_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(rim_grad)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            # Layer 7: Bottom shadow concentration
            dark = QRadialGradient(w * 0.50, h * 0.92, r * 0.10,
                                   w * 0.50, h * 0.80, r * 0.55)
            dark.setColorAt(0.0, QColor(0, 0, 0, 100))
            dark.setColorAt(0.5, QColor(0, 0, 0, 40))
            dark.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(dark)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            painter.restore()

            # Outer rim — subtle glass edge
            rim_a = skin["hover_rim_alpha"] if self._hover else skin["rim_alpha"]
            painter.setPen(QPen(QColor(255, 255, 255, rim_a + 10), 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(3, 3, w - 6, h - 6)

        elif st == "bubble":
            # ── BUBBLE: ultra-thin iridescent soap bubble ──
            # Clip to circle for all surface effects
            painter.save()
            clip_path = QPainterPath()
            clip_path.addEllipse(2, 2, w - 4, h - 4)
            painter.setClipPath(clip_path)

            # Nearly transparent body
            body_grad = QRadialGradient(w / 2, h / 2, r * 0.05, w / 2, h / 2, r)
            body_grad.setColorAt(0.0, QColor(255, 255, 255, 30))
            body_grad.setColorAt(0.3, ac(c, boost=40, sat_boost=skin["saturation_boost"],
                                          alpha=25))
            body_grad.setColorAt(0.7, ac(c, sat_boost=skin["saturation_boost"],
                                          factor=0.9, alpha=18))
            body_grad.setColorAt(1.0, QColor(200, 200, 200, 12))
            painter.setBrush(body_grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            # Iridescent film bands (rainbow interference pattern)
            import math as _m, time as _t
            shimmer = _t.time() * 12  # slow continuous shimmer
            for i in range(6):
                angle = i * 60 + shimmer
                bx = w / 2 + r * 0.55 * _m.cos(_m.radians(angle))
                by = h / 2 + r * 0.55 * _m.sin(_m.radians(angle))
                # Each band has a different hue shift
                hue_shift = i * 45
                ih, is_, iv, _ = c.getHsv()
                band_color = QColor.fromHsv(
                    (ih + hue_shift) % 360,
                    min(255, is_ + 60),
                    min(255, iv + 80),
                    40
                )
                band_grad = QRadialGradient(bx, by, r * 0.05, bx, by, r * 0.35)
                band_grad.setColorAt(0.0, band_color)
                band_grad.setColorAt(0.5, QColor(band_color.red(), band_color.green(),
                                                   band_color.blue(), 15))
                band_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setBrush(band_grad)
                painter.drawEllipse(2, 2, w - 4, h - 4)

            # Flowing rainbow band (top arc)
            for i in range(8):
                frac = i / 8.0
                arc_angle = -120 + frac * 240  # -120 to 120 degrees
                ax = w / 2 + r * 0.75 * _m.cos(_m.radians(arc_angle))
                ay = h / 2 + r * 0.75 * _m.sin(_m.radians(arc_angle))
                rainbow_hue = int(frac * 300) % 360
                arc_color = QColor.fromHsv(rainbow_hue, 150, 255, 30)
                ag = QRadialGradient(ax, ay, r * 0.03, ax, ay, r * 0.18)
                ag.setColorAt(0.0, arc_color)
                ag.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setBrush(ag)
                painter.drawEllipse(2, 2, w - 4, h - 4)

            painter.restore()

            # Bright specular (light hitting the bubble film)
            spec_grad = QRadialGradient(light_x, light_y - 2, r * skin["specular_size"],
                                         light_x, light_y - 2)
            spec_grad.setColorAt(0.0, QColor(255, 255, 255, skin["specular_alpha"]))
            spec_grad.setColorAt(0.25, QColor(255, 255, 255, 100))
            spec_grad.setColorAt(0.5, QColor(255, 255, 255, 25))
            spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(spec_grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            # Secondary highlight (bottom-left reflection)
            sec_grad = QRadialGradient(w * 0.62, h * 0.7, r * 0.08,
                                        w * 0.62, h * 0.7)
            sec_grad.setColorAt(0.0, QColor(255, 255, 255, 55))
            sec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(sec_grad)
            painter.drawEllipse(2, 2, w - 4, h - 4)

            # Thin membrane rim
            rim_a = skin["hover_rim_alpha"] if self._hover else skin["rim_alpha"]
            painter.setPen(QPen(QColor(255, 255, 255, rim_a), 1.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(3, 3, w - 6, h - 6)

        else:
            # ── DEFAULT / FROSTED: classic gradient sphere ──
            sphere_grad = QRadialGradient(light_x, light_y, r * 1.1,
                                           w / 2 + r * 0.15, h / 2 + r * 0.2)
            sphere_grad.setColorAt(0.0, ac(c, boost=skin["highlight_boost"],
                                           sat_boost=skin["saturation_boost"],
                                           alpha=255))
            sphere_grad.setColorAt(0.35, ac(c, sat_boost=skin["saturation_boost"],
                                            alpha=skin["mid_alpha"]))
            sphere_grad.setColorAt(0.7, ac(c, factor=skin["dark_factor"],
                                           sat_boost=skin["saturation_boost"],
                                           alpha=230))
            sphere_grad.setColorAt(1.0, ac(c, factor=skin["shadow_factor"],
                                           alpha=220))
            painter.setBrush(sphere_grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Specular
            spec_grad = QRadialGradient(light_x - 4, light_y - 6, r * skin["specular_size"],
                                         light_x - 4, light_y - 6)
            spec_grad.setColorAt(0.0, QColor(255, 255, 255, skin["specular_alpha"]))
            spec_grad.setColorAt(0.5, QColor(255, 255, 255, int(skin["specular_alpha"] * 0.25)))
            spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(spec_grad)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Frosted noise overlay
            if st == "frosted":
                random.seed(hash(self.category_data["name"]))
                for _ in range(80):
                    fx = random.randint(int(w * 0.15), int(w * 0.85))
                    fy = random.randint(int(h * 0.15), int(h * 0.85))
                    dx, dy = fx - w / 2, fy - h / 2
                    if dx * dx + dy * dy < (r - 10) * (r - 10):
                        fa = random.randint(10, 35)
                        painter.setPen(QPen(QColor(255, 255, 255, fa), 1))
                        painter.drawPoint(fx, fy)

        # ── Rim light ──
        rim_a = skin["hover_rim_alpha"] if self._hover else skin["rim_alpha"]
        painter.setPen(QPen(QColor(255, 255, 255, rim_a), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(3, 3, w - 6, h - 6)

        # ── Hover glow ──
        if self._hover and skin["hover_glow"]:
            glow_color = c if st == "neon" else QColor(255, 255, 255)
            glow_a = 50 if st == "neon" else 35
            glow_grad = QRadialGradient(w / 2, h / 2, r + 8, w / 2, h / 2, r)
            glow_grad.setColorAt(0.85, QColor(glow_color.red(), glow_color.green(),
                                               glow_color.blue(), 0))
            glow_grad.setColorAt(0.95, QColor(glow_color.red(), glow_color.green(),
                                               glow_color.blue(), glow_a))
            glow_grad.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(),
                                               glow_color.blue(), 0))
            painter.setBrush(glow_grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(-4, -4, w + 8, h + 8)

        # ── Text - category name ──
        text_alpha = 220 if st == "water" else 240
        painter.setPen(QColor(255, 255, 255, text_alpha))
        font = QFont("Microsoft YaHei", max(8, size // 10), QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, -4, w, h - 4), Qt.AlignCenter, self.category_data["name"])

        # Item count
        count = len(self.category_data.get("items", []))
        if count > 0:
            painter.setFont(QFont("Microsoft YaHei", max(6, size // 14)))
            painter.setPen(QColor(255, 255, 255, 160))
            painter.drawText(QRectF(0, h // 5, w, h), Qt.AlignCenter, f"{count} 项")

        painter.end()
        # Update cache metadata
        skin_key = self.current_skin
        if skin_key.startswith("custom:"):
            skin_key = "custom"
        self._cached_pixmap = pixmap
        self._cached_hover_state = self._hover
        self._cached_skin_key = skin_key
        self._cached_color = self.category_data.get("color", "#4A90D9")

    def paintEvent(self, event):
        """Transparent — spheres are drawn in parent _CircleArea.paintEvent."""
        pass

    def _ensure_cache(self):
        """Make sure the cached pixmap is rendered."""
        if not self._is_cache_valid():
            self._render_to_cache()

    def enterEvent(self, e):
        self._hover = True
        self._cached_pixmap = None  # invalidate cache for hover state
        self._ensure_cache()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._target_ox = 0.0
        self._target_oy = 0.0
        self._cached_pixmap = None  # invalidate cache for hover state
        self._ensure_cache()
        super().leaveEvent(e)

    def contextMenuEvent(self, e):
        self.menuRequested.emit(self)
        e.accept()


# ─── Radial Menu Overlay ────────────────────────────────────────────

class RadialMenu(QWidget):
    """Overlay showing app buttons arranged in a circle around a center point."""
    closed = pyqtSignal()
    appOpening = pyqtSignal()  # emitted before opening an app

    def __init__(self, category_data, center_pos, orbit_radius=0, parent=None):
        super().__init__(parent)
        self._closed_emitted = False
        self.category_data = category_data
        self.center_pos = center_pos
        self._orbit_radius = orbit_radius
        self._app_buttons = []
        self._target_positions = []  # (x, y) for each button
        self._anim_progress = 0.0    # 0.0 -> 1.0 during open animation
        self._pulse_phase = 0.0      # for center circle pulse
        self._bounce_phase = 0.0     # for sphere bounce
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._setup_geometry()
        self._create_buttons()
        self._start_animation()
        self.show()

    def _setup_geometry(self):
        radius = self._calc_radius()
        margin = 160
        size = int((radius + margin) * 2)
        x = self.center_pos.x() - size // 2
        y = self.center_pos.y() - size // 2
        self.setGeometry(x, y, size, size)

    def _calc_radius(self):
        if self._orbit_radius > 0:
            return self._orbit_radius
        n = len(self.category_data.get("items", []))
        if n <= 1:
            return 160
        if n <= 4:
            return 180
        if n <= 6:
            return 200
        return 220

    def _create_buttons(self):
        items = self.category_data.get("items", [])
        color = self.category_data.get("color", "#4A90D9")
        radius = self._calc_radius()
        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2

        if not items:
            return

        angle_step = 360.0 / len(items)
        start_angle = -90

        for i, item in enumerate(items):
            angle = math.radians(start_angle + i * angle_step)
            tx = int(cx + radius * math.cos(angle) - 70)
            ty = int(cy + radius * math.sin(angle) - 70)
            self._target_positions.append((tx, ty))

            btn = AppButton(item["name"], color, "", self)  # defer icon loading
            btn.move(int(cx) - 70, int(cy) - 70)  # Start at center
            btn.clicked.connect(lambda checked, it=item: self._open_item(it))
            btn.rightClicked.connect(lambda it=item: self._show_item_menu(it))
            btn.hide()  # show on first animation tick to avoid burst
            self._app_buttons.append(btn)

        # Load icons on a background thread
        QTimer.singleShot(150, lambda: self._load_icons_threaded(items))

    def _load_icons_threaded(self, items):
        from PyQt5.QtCore import QThread
        class _IconLoader(QThread):
            def run(s):
                for i, item in enumerate(items):
                    path = item.get("path", "")
                    if not path:
                        s._results.append(None)
                        continue
                    pm = get_icon_pixmap(path, 80)
                    s._results.append(pm)
        loader = _IconLoader(self)
        loader._results = []
        loader.finished.connect(
            lambda: self._apply_icons(loader._results, len(items)))
        loader.start()

    def _apply_icons(self, results, total):
        for i, pm in enumerate(results):
            if pm and i < len(self._app_buttons):
                self._app_buttons[i]._icon_pixmap = pm
                self._app_buttons[i]._cached_sphere = None

    def _start_animation(self):
        """Animate buttons flying from center to target positions."""
        self._anim_progress = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_step)
        self._anim_timer.start(20)  # ~50fps

        # Pulse timer for center circle
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_step)
        self._pulse_timer.start(50)

    @staticmethod
    def _spring_ease(t):
        """Bouncy spring easing: overshoots then settles."""
        return 1 - math.cos(t * math.pi * 2.5) * math.exp(-t * 6)

    def _animate_step(self):
        try:
            self._anim_progress += 0.04
            if self._anim_progress >= 1.0:
                self._anim_progress = 1.0
                self._anim_timer.stop()
            cx = self.width() / 2
            cy = self.height() / 2
            n = len(self._app_buttons)
            for i, btn in enumerate(self._app_buttons):
                if not btn.isVisible():
                    btn.show()
                delay = i * 0.06
                raw_t = max(0.0, min(1.0, (self._anim_progress - delay) / max(0.01, 1 - delay * (n - 1) / max(1, n))))
                t = raw_t
                if t <= 0:
                    btn._anim_opacity = 0
                    btn._anim_scale = 0
                    btn.update()
                    continue
                pos_ease = 1 - (1 - t) ** 3
                scale = self._spring_ease(min(1.0, t * 1.2))
                scale = max(0.0, min(1.15, scale))
                if i < len(self._target_positions):
                    tx, ty = self._target_positions[i]
                    cur_x = cx - 70 + (tx - (cx - 70)) * pos_ease
                    cur_y = cy - 70 + (ty - (cy - 70)) * pos_ease
                    btn.move(int(cur_x), int(cur_y))
                btn._anim_opacity = min(1.0, t * 3)
                btn._anim_scale = scale
                btn.update()
            self.update()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("RadialMenu _animate_step failed: %s", exc)

    def _pulse_step(self):
        try:
            if self._anim_timer.isActive():
                return
            self._pulse_phase += 0.08
            self._bounce_phase += 0.12
            for i, btn in enumerate(self._app_buttons):
                if i < len(self._target_positions):
                    tx, ty = self._target_positions[i]
                    offset = math.sin(self._bounce_phase + i * 1.2) * 6
                    scale_bounce = 1.0 + 0.04 * math.sin(self._bounce_phase + i * 1.2)
                    btn.move(tx, ty + int(offset))
                    btn._anim_scale = scale_bounce
                    btn.update()
            self.update()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("RadialMenu _pulse_step failed: %s", exc)

    def _open_item(self, item):
        path = item.get("path", "")
        self.appOpening.emit()
        self.close()
        if path:
            # Resolve bare filenames via PATH
            resolved = _resolve_path(path)
            if resolved and os.path.exists(resolved):
                try:
                    os.startfile(resolved)
                except Exception as e:
                    self._log(f"Failed to launch {resolved}: {e}")
            else:
                # Try raw path as fallback (URLs, protocols, etc.)
                try:
                    os.startfile(path)
                except Exception:
                    # Show error notification
                    parent = self.parent()
                    if parent:
                        try:
                            QTimer.singleShot(500, lambda: QMessageBox.warning(
                                parent, "启动失败",
                                f"无法找到或启动：\n{path}\n\n请右键编辑该应用，检查路径是否正确。"))
                        except Exception:
                            pass

    def _show_item_menu(self, item):
        """Show context menu for an app item in the radial menu."""
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("▶ 打开", lambda: self._open_item(item))
        if item.get("path"):
            def _open_location():
                import subprocess
                path = item["path"]
                if os.path.isfile(path):
                    subprocess.Popen(["explorer", "/select,", path])
                elif os.path.isdir(path):
                    subprocess.Popen(["explorer", path])
            menu.addAction("📁 打开文件所在位置", _open_location)
        menu.addSeparator()
        menu.addAction("✏️ 编辑", lambda: self._edit_item(item))
        menu.addAction("🗑️ 移除", lambda: self._remove_item(item))
        menu.exec_(QCursor.pos())

    def _edit_item(self, item):
        """Edit app name and path."""
        from PyQt5.QtWidgets import QFileDialog
        name, ok = QInputDialog.getText(self, "编辑项目", "名称：", text=item.get("name", ""))
        if not ok:
            return
        if name.strip():
            item["name"] = name.strip()
        # Path editor with browse button
        path_dlg = QDialog(self)
        path_dlg.setWindowTitle("编辑路径")
        path_dlg.setMinimumWidth(400)
        path_dlg.setStyleSheet("""
            QDialog { background: rgba(22,24,34,255); color: white; border: 1px solid rgba(196,180,140,40); border-radius: 12px; }
            QLabel { color: rgba(255,255,255,200); }
            QLineEdit { background: rgba(40,42,54,200); color: white; border: 1px solid rgba(196,180,140,40); border-radius: 6px; padding: 6px; }
            QPushButton { background: rgba(196,180,140,40); color: white; border: 1px solid rgba(196,180,140,60); border-radius: 6px; padding: 6px 12px; }
            QPushButton:hover { background: rgba(196,180,140,70); }
        """)
        lay = QVBoxLayout(path_dlg)
        lay.addWidget(QLabel("程序路径："))
        path_row = QHBoxLayout()
        path_edit = QLineEdit(item.get("path", ""))
        path_row.addWidget(path_edit)
        browse_btn = QPushButton("浏览...")
        def _browse():
            f, _ = QFileDialog.getOpenFileName(path_dlg, "选择程序", "", "可执行文件 (*.exe *.lnk *.bat *.cmd);;所有文件 (*)")
            if f:
                path_edit.setText(f)
        browse_btn.clicked.connect(_browse)
        path_row.addWidget(browse_btn)
        lay.addLayout(path_row)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(path_dlg.accept)
        btns.rejected.connect(path_dlg.reject)
        lay.addWidget(btns)
        if path_dlg.exec_() == QDialog.Accepted:
            item["path"] = _to_storage_path(path_edit.text().strip())
        self.category_data["items"].sort(key=lambda x: x.get("name", ""))
        self._save_and_close()

    def _remove_item(self, item):
        if item in self.category_data["items"]:
            self.category_data["items"].remove(item)
            self._save_and_close()

    def _save_and_close(self):
        self.closed.emit()
        self.close()

    def paintEvent(self, event):
        try:
            self._paint_content(event)
        except Exception:
            pass

    def _paint_content(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        color = QColor(self.category_data.get("color", "#4A90D9"))
        progress = self._anim_progress

        # Draw orbit ring (animated) with warm accent
        orbit_r = self._calc_radius()
        ring_alpha = int(40 * progress)
        painter.setPen(QPen(QColor(196, 180, 140, ring_alpha), 1, Qt.DotLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - orbit_r), int(cy - orbit_r), orbit_r * 2, orbit_r * 2)

        # Draw connecting lines from center to each button
        line_alpha = int(45 * progress)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), line_alpha), 0.8, Qt.DotLine))
        for i, btn in enumerate(self._app_buttons):
            bx = btn.x() + btn.width() / 2
            by = btn.y() + btn.height() / 2
            painter.drawLine(int(cx), int(cy), int(bx), int(by))

        # Center circle with pulse effect
        pulse = 1.0 + 0.03 * math.sin(self._pulse_phase)
        center_r = int(42 * pulse * min(progress * 2, 1.0))

        # Glow ring around center
        glow_alpha = int(30 * progress * (0.5 + 0.5 * math.sin(self._pulse_phase)))
        painter.setPen(Qt.NoPen)
        glow_grad = QRadialGradient(cx, cy, center_r, cx, cy, center_r + 12)
        glow_grad.setColorAt(0.7, QColor(color.red(), color.green(), color.blue(), glow_alpha))
        glow_grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
        painter.setBrush(glow_grad)
        painter.drawEllipse(int(cx - center_r - 12), int(cy - center_r - 12),
                           (center_r + 12) * 2, (center_r + 12) * 2)

        # Main center circle with gradient
        body_grad = QRadialGradient(cx - 5, cy - 8, center_r * 0.3, cx, cy, center_r)
        body_grad.setColorAt(0.0, QColor(min(255, color.red() + 60),
                                          min(255, color.green() + 60),
                                          min(255, color.blue() + 60), int(230 * progress)))
        body_grad.setColorAt(0.5, QColor(color.red(), color.green(), color.blue(), int(210 * progress)))
        body_grad.setColorAt(1.0, QColor(int(color.red() * 0.6), int(color.green() * 0.6),
                                          int(color.blue() * 0.6), int(220 * progress)))
        painter.setBrush(body_grad)
        painter.drawEllipse(int(cx - center_r), int(cy - center_r), center_r * 2, center_r * 2)

        # Category name
        painter.setPen(QColor(255, 255, 255, int(220 * progress)))
        font = painter.font()
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.category_data.get("name", ""))
        painter.drawEllipse(int(cx - center_r), int(cy - center_r), center_r * 2, center_r * 2)

        # Ring border with gold accent
        border_alpha = int(90 * progress)
        painter.setPen(QPen(QColor(196, 180, 140, border_alpha), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - center_r), int(cy - center_r), center_r * 2, center_r * 2)

        # Center text
        if progress > 0.3:
            text_alpha = int(255 * min((progress - 0.3) / 0.3, 1.0))
            painter.setPen(QColor(255, 255, 255, text_alpha))
            painter.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
            painter.drawText(QRectF(cx - center_r, cy - center_r, center_r * 2, center_r * 2),
                           Qt.AlignCenter, self.category_data["name"])

        painter.end()

    def mousePressEvent(self, e):
        w, h = self.width(), self.height()
        cx = w / 2
        cy = h / 2
        dist = math.sqrt((e.x() - cx) ** 2 + (e.y() - cy) ** 2)
        if dist < 45:
            self._show_center_menu()
            return
        for btn in self._app_buttons:
            if btn.geometry().contains(e.pos()):
                return
        self.close()

    def _show_center_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("重命名分类", self._rename)
        menu.addAction("更改颜色", self._change_color)
        menu.addAction("添加项目", self._add_item)
        menu.addSeparator()
        menu.addAction("删除分类", self._delete)
        menu.exec_(QCursor.pos())

    def _rename(self):
        name, ok = QInputDialog.getText(self, "重命名", "新名称：",
                                         text=self.category_data["name"])
        if ok and name.strip():
            self.category_data["name"] = name.strip()
            self.closed.emit()
            self.close()

    def _change_color(self):
        color = QColorDialog.getColor(QColor(self.category_data["color"]), self, "选择颜色")
        if color.isValid():
            self.category_data["color"] = color.name()
            self.closed.emit()
            self.close()

    def _add_item(self):
        name, ok = QInputDialog.getText(self, "添加项目", "项目名称：")
        if ok and name.strip():
            path, ok2 = QInputDialog.getText(self, "添加项目", "路径（可留空）：")
            raw = path.strip() if ok2 else ""
            self.category_data["items"].append({
                "name": name.strip(),
                "path": _to_storage_path(raw) if raw else ""
            })
            self.closed.emit()
            self.close()

    def _delete(self):
        reply = QMessageBox.question(self, "确认删除",
            f'确定删除分类 "{self.category_data["name"]}"？',
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.category_data["_deleted"] = True
            self.closed.emit()
            self.close()

    def closeEvent(self, e):
        # Stop timers to prevent callbacks after destruction
        if hasattr(self, '_anim_timer'):
            self._anim_timer.stop()
        if hasattr(self, '_pulse_timer'):
            self._pulse_timer.stop()
        if not self._closed_emitted:
            self._closed_emitted = True
            self.closed.emit()
        super().closeEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()


# ─── Bottom Toolbar Button ──────────────────────────────────────────

class ToolButton(QPushButton):
    def __init__(self, icon_text, tooltip, color="#4A90D9", parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self.setText(icon_text)
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.base_color = color
        self._hover = False
        self._update_style(False)

    def _update_style(self, hover):
        c = self.base_color
        col = QColor(c)
        if hover:
            bg = f"rgba({col.red()},{col.green()},{col.blue()},45)"
            border_alpha = 200
            text_alpha = 255
        else:
            bg = "transparent"
            border_alpha = 120
            text_alpha = 180
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: rgba({col.red()},{col.green()},{col.blue()},{text_alpha});
                border: 1.5px solid rgba({col.red()},{col.green()},{col.blue()},{border_alpha});
                border-radius: 22px;
                font-size: 18px;
                font-weight: bold;
            }}
        """)

    def enterEvent(self, e):
        self._hover = True
        self._update_style(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._update_style(False)
        super().leaveEvent(e)


# ─── Main Window ──────────────────────────────────────────────────────

# ─── Circle Area (draws orbit ring behind category buttons) ─────────

class _CircleArea(QWidget):
    """3D rotatable ring showing category buttons."""
    categoryClicked = pyqtSignal(object)      # emits category_data
    categoryMenuRequested = pyqtSignal(object) # emits button widget

    def __init__(self, parent=None, wallpaper_manager=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)
        self._phase = 0.0
        self._btn_entries = []  # [(btn, angle), ...]
        self._wallpaper_manager = wallpaper_manager
        self._size_scale = 1.0  # 球体大小缩放

        # Ring tilt angle (how much the ring is tilted toward the viewer)
        self._tilt = 0.55
        # Current rotation angle of the ring
        self._angle = 0.0

        # Mouse follow state
        self._mouse_active = False
        self._mouse_x = 0.0

        # Ring position offset (for move mode)
        self._ring_offset_x = 0
        self._ring_offset_y = 0
        # Move mode state
        self._move_mode = False
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_orig_ox = 0
        self._drag_orig_oy = 0

        # Fly-in animation
        self._flying_in = False

        # Paint cache (avoids recreating objects every frame)
        self._cached_bg_pixmap = None
        self._cached_bg_size = None
        self._cached_vignette = None
        self._cached_vignette_size = None
        self._flyin_progress = 0.0
        self._flyin_targets = []
        self._projected = []  # computed by _update_positions, drawn in paintEvent
        self._hovered_btn = None  # currently hovered category button (manual tracking)

        # Custom background
        self._bg_pixmap = None
        bg_image = self._get_data("bg_image")
        if bg_image and os.path.exists(bg_image):
            self._bg_pixmap = QPixmap(bg_image)

        # Event filter to capture mouse over child buttons
        self.installEventFilter(self)

        from PyQt5.QtCore import QTimer
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._render_tick)
        self._render_timer.start(33)

    # ── Public API ──────────────────────────────────────────────
    def _get_data(self, key, default=None):
        """Read a setting from parent's in-memory data (no disk I/O)."""
        parent = self.parent()
        if parent and hasattr(parent, 'data'):
            return parent.data.get(key, default)
        return default

    def _set_data(self, key, value):
        """Push a setting change to parent's in-memory data."""
        parent = self.parent()
        if parent and hasattr(parent, 'data'):
            parent.data[key] = value

    def set_buttons(self, categories, flyin=True):
        """Create buttons for categories on a ring, optionally with fly-in animation."""
        # Clean up ALL existing buttons (including during fly-in animation)
        for btn, *_ in self._btn_entries:
            btn.deleteLater()
        for btn, *_ in self._flyin_targets:
            btn.deleteLater()
        # Safety net: remove any orphaned CategoryCircleButtons
        for btn in self.findChildren(CategoryCircleButton):
            btn.deleteLater()
        self._btn_entries = []
        self._flyin_targets = []
        self._flying_in = False

        if not categories:
            return

        n = len(categories)
        # Auto scale: ensure ~180px arc between spheres, cap at 0.50
        base = min(self.width(), self.height())
        ring_r = min(240 * n / (2 * math.pi), base * 0.55) if n > 0 else base * 0.40

        targets = []
        for i, cat in enumerate(categories):
            angle = 2 * math.pi * i / n

            btn = CategoryCircleButton(cat, self)
            btn.clicked.connect(lambda checked, c=cat: self.categoryClicked.emit(c))
            btn.menuRequested.connect(lambda b=btn: self.categoryMenuRequested.emit(b))
            btn.installEventFilter(self)

            # Hide child widget — spheres are drawn in our paintEvent
            btn.hide()
            btn._ensure_cache()  # pre-render sphere pixmap for parent to draw
            targets.append((btn, angle))

        self._btn_entries = targets
        if flyin:
            self._flyin_targets = targets
            self._flying_in = True
            self._flyin_progress = 0.0

    # ── 3D Ring Math ───────────────────────────────────────────
    def _ring_point(self, angle, radius):
        """Get 3D point on ring, then tilt and rotate it."""
        # Point on ring in XZ plane
        x = radius * math.cos(angle)
        z = radius * math.sin(angle)
        y = 0
        # Tilt ring toward viewer (rotate around X axis)
        cos_t, sin_t = math.cos(self._tilt), math.sin(self._tilt)
        y2 = y * cos_t - z * sin_t
        z2 = y * sin_t + z * cos_t
        # Spin ring (rotate around Y axis)
        cos_a, sin_a = math.cos(self._angle), math.sin(self._angle)
        x2 = x * cos_a + z2 * sin_a
        z3 = -x * sin_a + z2 * cos_a
        return x2, y2, z3

    # ── Render Loop ─────────────────────────────────────────────
    def _render_tick(self):
        # ── fully idle: skip render with aggressive frame dropping ──
        if not self._flying_in and not self._mouse_active and not self._move_mode and not self._dragging:
            if not hasattr(self, '_idle_counter'):
                self._idle_counter = 0
            self._idle_counter += 1
            # Every 16th frame (~2 Hz) do a soft phase-only update (no repaint)
            if self._idle_counter % 16 != 0:
                return
        self._phase += 0.02

        # Fly-in animation
        if self._flying_in:
            self._flyin_progress += 0.025
            if self._flyin_progress >= 1.0:
                self._flyin_progress = 1.0
                self._flying_in = False
                self._btn_entries = list(self._flyin_targets)
            self._update_positions(self._flyin_targets, self._flyin_progress)
            self.update()
            return

        # Slow auto-rotate
        self._angle += 0.012 if self._mouse_active else 0.005

        # Mouse influences rotation speed
        if self._mouse_active:
            ratio = (self._mouse_x - self.width() / 2) / (self.width() / 2)
            self._angle += ratio * 0.04

        # Animate hover offsets — skip when settled
        any_dirty = False
        for btn, angle in self._btn_entries:
            ox = btn.hover_ox + (btn._target_ox - btn.hover_ox) * 0.18
            oy = btn.hover_oy + (btn._target_oy - btn.hover_oy) * 0.18
            if abs(ox - btn.hover_ox) > 0.01 or abs(oy - btn.hover_oy) > 0.01:
                any_dirty = True
            btn.hover_ox = ox
            btn.hover_oy = oy

        self._update_positions(self._btn_entries)
        # Only repaint if hover offsets changed or not idle
        if any_dirty or not hasattr(self, '_idle_counter') or self._idle_counter % 16 == 0:
            self.update()

    def _update_positions(self, entries, flyin_t=1.0):
        """Compute 3D projections for all buttons. NO widget manipulation —
        spheres are drawn in paintEvent for maximum performance."""
        n = len(entries)
        base = min(self.width(), self.height())
        ring_r = min(240 * n / (2 * math.pi), base * 0.55) * flyin_t if n > 0 else base * 0.40 * flyin_t
        ring_r *= self._size_scale
        tilt = 0.55
        cx = self.width() / 2 + self._ring_offset_x
        cy = self.height() / 2 - ring_r * math.sin(tilt) * 0.6 + self._ring_offset_y
        fov = 600

        projected = []
        for btn, angle in entries:
            a = angle + self._angle
            x = ring_r * math.cos(a)
            z = ring_r * math.sin(a)
            cos_t, sin_t = math.cos(tilt), math.sin(tilt)
            y2 = 0 * cos_t - z * sin_t
            z2 = 0 * sin_t + z * cos_t
            depth = z2 + fov
            if depth < 1:
                depth = 1
            scale = fov / depth
            sx = cx + x * scale + btn.hover_ox
            sy = cy + y2 * scale + btn.hover_oy
            base_size = 160
            sz = max(30, int(base_size * scale))
            opacity = max(0.3, min(1.0, 0.4 + 0.6 * scale))
            projected.append((btn, sx, sy, sz, opacity, z2))

        # Sort by depth (back to front)
        projected.sort(key=lambda p: p[5])
        self._projected = projected

    # ── Mouse Interaction ───────────────────────────────────────
    def _hit_test(self, mx, my):
        """Find the category button at screen position (mx, my).
        Returns (btn, category_data) or (None, None)."""
        best = None
        best_dist = float('inf')
        for btn, sx, sy, sz, opacity, _ in self._projected:
            half = sz / 2
            dx = mx - sx
            dy = my - sy
            if abs(dx) <= half and abs(dy) <= half:
                dist = dx * dx + dy * dy
                if dist < best_dist:
                    best_dist = dist
                    best = btn
        return best

    def _set_hover(self, btn):
        """Update hover state for category buttons."""
        if btn == self._hovered_btn:
            return
        old = self._hovered_btn
        self._hovered_btn = btn
        if old and old is not btn:
            old._hover = False
            old._target_ox = 0.0
            old._target_oy = 0.0
            old._cached_pixmap = None  # invalidate cache
            old._ensure_cache()        # re-render non-hovered pixmap
        if btn:
            btn._hover = True
            btn._cached_pixmap = None  # invalidate for hover state
            btn._ensure_cache()        # re-render hovered pixmap

    def mousePressEvent(self, e):
        """Handle mouse press — click on sphere or start drag."""
        if self._move_mode and e.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_x = e.globalX()
            self._drag_start_y = e.globalY()
            self._drag_orig_ox = self._ring_offset_x
            self._drag_orig_oy = self._ring_offset_y
            e.accept()
            return
        # Manual click detection on spheres
        if e.button() == Qt.LeftButton:
            btn = self._hit_test(e.x(), e.y())
            if btn:
                # Find the category data for this button
                for b, *_ in self._btn_entries:
                    if b is btn:
                        self.categoryClicked.emit(b.category_data)
                        e.accept()
                        return
        elif e.button() == Qt.RightButton:
            btn = self._hit_test(e.x(), e.y())
            if btn:
                self.categoryMenuRequested.emit(btn)
                e.accept()
                return
        super().mousePressEvent(e)

    def eventFilter(self, obj, e):
        from PyQt5.QtCore import QEvent
        if e.type() == QEvent.MouseMove:
            pos = self.mapFromGlobal(QCursor.pos())
            self._mouse_active = True
            self._mouse_x = pos.x()
            # Manual hover detection
            btn = self._hit_test(pos.x(), pos.y())
            self._set_hover(btn)
            if btn:
                # Compute elastic follow offset
                cx, cy = self.width() / 2, self.height() / 2
                # Find the projected position for this button
                for b, sx, sy, sz, op, _ in self._projected:
                    if b is btn:
                        btn._target_ox = (pos.x() - sx) * 0.5
                        btn._target_oy = (pos.y() - sy) * 0.5
                        break
        elif e.type() == QEvent.Leave:
            self._mouse_active = False
            self._set_hover(None)
        elif e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
            if self._move_mode:
                self._dragging = True
                self._drag_start_x = e.globalX()
                self._drag_start_y = e.globalY()
                self._drag_orig_ox = self._ring_offset_x
                self._drag_orig_oy = self._ring_offset_y
                e.accept()
                return True
        return False

    def mouseMoveEvent(self, e):
        if self._dragging:
            dx = e.globalX() - self._drag_start_x
            dy = e.globalY() - self._drag_start_y
            self._ring_offset_x = self._drag_orig_ox + dx
            self._ring_offset_y = self._drag_orig_oy + dy
            self._update_positions(self._btn_entries)
            return
        self._mouse_active = True
        self._mouse_x = e.x()

    def leaveEvent(self, e):
        self._mouse_active = False
        self._set_hover(None)

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self._dragging = False

    # ── Paint (background decorations) ─────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        # 壁纸模式：跳过背景和装饰，只画球体
        if not getattr(self, '_wallpaper_mode', False):
            # Custom background image or color (wallpaper engine)
            bg_color = self._get_data("bg_color")
            if self._wallpaper_manager and self._wallpaper_manager.get_type() != "transparent":
                self._wallpaper_manager.paint(painter, self.rect())
                wp_type = self._wallpaper_manager.get_type()
                if wp_type in ("image", "video"):
                    painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 100))
            elif self._bg_pixmap and not self._bg_pixmap.isNull():
                # Cache the scaled pixmap (only re-scale when size changes)
                if self._cached_bg_size != (w, h):
                    self._cached_bg_pixmap = self._bg_pixmap.scaled(
                        w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    self._cached_bg_size = (w, h)
                if self._cached_bg_pixmap:
                    sw, sh = self._cached_bg_pixmap.width(), self._cached_bg_pixmap.height()
                    x = (w - sw) // 2
                    y = (h - sh) // 2
                    painter.drawPixmap(x, y, self._cached_bg_pixmap)
                painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 100))
            elif bg_color and bg_color != "transparent":
                painter.fillRect(0, 0, w, h, QColor(bg_color))

            # Cache vignette gradient (only recreate when size changes)
            if self._cached_vignette_size != (w, h):
                vignette = QRadialGradient(cx, cy, max(w, h) * 0.55, cx, cy)
                vignette.setColorAt(0.5, QColor(0, 0, 0, 0))
                vignette.setColorAt(0.85, QColor(0, 0, 0, 12))
                vignette.setColorAt(1.0, QColor(0, 0, 0, 30))
                self._cached_vignette = QBrush(vignette)
                self._cached_vignette_size = (w, h)
            painter.fillRect(0, 0, w, h, self._cached_vignette)

            # Subtle grid / orbit decoration with warm tone
            painter.setPen(QPen(QColor(196, 180, 140, 14), 1, Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            r = min(cx, cy) - 30
            painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

            # Center decoration with warm gold glow
            glow = int(18 + 10 * math.sin(self._phase))
            painter.setPen(QPen(QColor(196, 180, 140, glow), 1.5))
            painter.drawEllipse(int(cx - r + 15), int(cy - r + 15),
                               int((r - 15) * 2), int((r - 15) * 2))

            # Secondary inner ring
            glow2 = int(8 + 5 * math.sin(self._phase * 1.3 + 1))
            painter.setPen(QPen(QColor(196, 180, 140, glow2), 0.8))
            painter.drawEllipse(int(cx - r + 30), int(cy - r + 30),
                               int((r - 30) * 2), int((r - 30) * 2))

            # Center text with subtle glow
            painter.setPen(QColor(196, 180, 140, 40))
            painter.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
            painter.drawText(QRectF(cx - 60, cy - 18, 120, 36), Qt.AlignCenter, "桌面收纳")

        # ── Draw category spheres (rendered in parent, not by child widgets) ──
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        for btn, sx, sy, sz, opacity, _ in self._projected:
            pixmap = getattr(btn, '_cached_pixmap', None)
            if pixmap and not pixmap.isNull():
                painter.setOpacity(opacity)
                half = sz // 2
                painter.drawPixmap(int(sx - half), int(sy - half), sz, sz, pixmap)
        painter.setOpacity(1.0)

        # Hover tooltip — category name + item count
        if self._hovered_btn:
            cat = self._hovered_btn.category_data
            name = cat.get("name", "")
            count = len(cat.get("items", []))
            # Find this button's projected position
            for btn, sx, sy, sz, _, _ in self._projected:
                if btn is self._hovered_btn:
                    text = f"{name} ({count}项)" if count else name
                    font = QFont("Microsoft YaHei", 10, QFont.Bold)
                    painter.setFont(font)
                    fm = painter.fontMetrics()
                    tw = fm.horizontalAdvance(text) + 16
                    th = fm.height() + 8
                    tx = int(sx - tw / 2)
                    ty = int(sy + sz / 2 + 8)
                    # Background pill
                    painter.setOpacity(0.85)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(20, 22, 32, 220))
                    painter.drawRoundedRect(tx, ty, tw, th, 6, 6)
                    painter.setOpacity(1.0)
                    painter.setPen(QColor(230, 220, 190))
                    painter.drawText(tx, ty, tw, th, Qt.AlignCenter, text)
                    break

        painter.end()

    def closeEvent(self, e):
        self._render_timer.stop()
        super().closeEvent(e)

    def sizeHint(self):
        return QSize(600, 600)


class SkinPreview(QWidget):
    """Preview widget that renders a sphere with given skin parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self._skin = dict(SPHERE_SKINS["default"])
        self._color = QColor("#4A90D9")

    def update_skin(self, skin_dict, color=None):
        self._skin = dict(skin_dict)
        if color:
            self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        c = self._color
        r = min(w, h) / 2
        skin = self._skin
        st = skin.get("style", "default")

        def ac(color, boost=0, sat_boost=0, factor=1.0, alpha=255):
            hh, ss, vv, _ = color.getHsv()
            ss = min(255, max(0, ss + sat_boost))
            vv = min(255, max(0, int(vv * factor)))
            nc = QColor.fromHsv(hh, ss, vv, alpha)
            if boost:
                nc = QColor(min(255, nc.red() + boost),
                            min(255, nc.green() + boost),
                            min(255, nc.blue() + boost), alpha)
            return nc

        light_x = w * 0.35
        light_y = h * 0.3

        if st == "neon":
            dark = ac(c, boost=0, sat_boost=skin.get("saturation_boost", 0),
                      factor=0.15, alpha=skin.get("mid_alpha", 200))
            inner = QRadialGradient(w / 2, h / 2, r * 0.85, w / 2, h / 2, r)
            inner.setColorAt(0.0, QColor(0, 0, 0, 180))
            inner.setColorAt(0.7, dark)
            inner.setColorAt(1.0, ac(c, boost=skin.get("highlight_boost", 80),
                                     sat_boost=skin.get("saturation_boost", 0),
                                     factor=0.5, alpha=200))
            painter.setBrush(inner)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            for i in range(3):
                a_val = skin.get("rim_alpha", 80) - i * 20
                if a_val <= 0:
                    break
                painter.setPen(QPen(ac(c, boost=skin.get("highlight_boost", 80),
                                       sat_boost=skin.get("saturation_boost", 0),
                                       alpha=a_val), 3.5 - i * 0.8))
                painter.setBrush(Qt.NoBrush)
                off = 2 + i * 2
                painter.drawEllipse(off, off, w - off * 2, h - off * 2)
        elif st == "crystal":
            # Glass body
            body = QRadialGradient(w * 0.48, h * 0.40, r * 0.12, w * 0.50, h * 0.50, r)
            body.setColorAt(0.00, QColor(255, 255, 255, 230))
            body.setColorAt(0.06, ac(c, boost=100, sat_boost=30, alpha=255))
            body.setColorAt(0.20, ac(c, boost=40, sat_boost=15, alpha=250))
            body.setColorAt(0.45, ac(c, factor=0.55, alpha=240))
            body.setColorAt(0.70, ac(c, factor=0.25, alpha=220))
            body.setColorAt(1.00, ac(c, factor=0.06, alpha=170))
            painter.setBrush(body)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Primary specular
            spec = QRadialGradient(w * 0.38, h * 0.22, r * 0.04,
                                   w * 0.38, h * 0.22, r * 0.30)
            spec.setColorAt(0.0, QColor(255, 255, 255, 255))
            spec.setColorAt(0.06, QColor(255, 255, 255, 220))
            spec.setColorAt(0.20, QColor(255, 255, 255, 100))
            spec.setColorAt(0.45, QColor(255, 255, 255, 20))
            spec.setColorAt(0.70, QColor(255, 255, 255, 0))
            painter.setBrush(spec)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Secondary specular
            spec2 = QRadialGradient(w * 0.62, h * 0.30, r * 0.02,
                                    w * 0.62, h * 0.30, r * 0.10)
            spec2.setColorAt(0.0, QColor(255, 255, 255, 180))
            spec2.setColorAt(0.20, QColor(255, 255, 255, 60))
            spec2.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(spec2)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            # Sparkle dots
            for sx, sy, sr, sa in [(0.30, 0.40, 0.015, 150),
                                    (0.55, 0.20, 0.012, 130),
                                    (0.70, 0.45, 0.013, 110)]:
                sp = QRadialGradient(w * sx, h * sy, r * sr * 0.3,
                                     w * sx, h * sy, r * sr)
                sp.setColorAt(0.0, QColor(255, 255, 255, sa))
                sp.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(sp)
                painter.drawEllipse(2, 2, w - 4, h - 4)
            # Rim light
            rim_g = QRadialGradient(w / 2, h / 2, r * 0.75, w / 2, h / 2, r)
            rim_g.setColorAt(0.0, QColor(255, 255, 255, 0))
            rim_g.setColorAt(0.75, QColor(255, 255, 255, 0))
            rim_g.setColorAt(0.90, QColor(255, 255, 255, 35))
            rim_g.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(rim_g)
            painter.drawEllipse(2, 2, w - 4, h - 4)
        else:
            sphere = QRadialGradient(light_x, light_y, r * 1.1,
                                     w / 2 + r * 0.15, h / 2 + r * 0.2)
            sphere.setColorAt(0.0, ac(c, boost=skin.get("highlight_boost", 120),
                                      sat_boost=skin.get("saturation_boost", 0), alpha=255))
            sphere.setColorAt(0.35, ac(c, sat_boost=skin.get("saturation_boost", 0),
                                       alpha=skin.get("mid_alpha", 240)))
            sphere.setColorAt(0.7, ac(c, factor=skin.get("dark_factor", 0.7),
                                      sat_boost=skin.get("saturation_boost", 0), alpha=230))
            sphere.setColorAt(1.0, ac(c, factor=skin.get("shadow_factor", 0.3), alpha=220))
            painter.setBrush(sphere)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, w - 4, h - 4)
            spec = QRadialGradient(light_x - 4, light_y - 6, r * skin.get("specular_size", 0.25),
                                   light_x - 4, light_y - 6)
            spec.setColorAt(0.0, QColor(255, 255, 255, skin.get("specular_alpha", 160)))
            spec.setColorAt(0.5, QColor(255, 255, 255, int(skin.get("specular_alpha", 160) * 0.25)))
            spec.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(spec)
            painter.drawEllipse(2, 2, w - 4, h - 4)

        painter.setPen(QPen(QColor(255, 255, 255, skin.get("rim_alpha", 15)), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(3, 3, w - 6, h - 6)
        painter.end()


class CustomSkinDialog(QDialog):
    """Dialog for creating/editing a custom sphere skin."""

    def __init__(self, parent=None, existing=None, color="#4A90D9"):
        super().__init__(parent)
        self.setWindowTitle("自定义皮肤")
        self.setFixedSize(480, 620)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22,24,34,255), stop:1 rgba(14,16,22,255));
                color: white;
                border: 1px solid rgba(196,180,140,40);
                border-radius: 14px;
            }
            QLabel { color: rgba(210,210,220,210); font-size: 13px; }
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255,255,255,12);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 18px; height: 18px; margin: -6px 0;
                background: qradialgradient(cx:0.35, cy:0.35, radius:0.6,
                    stop:0 rgba(220,210,180,255), stop:1 rgba(180,168,130,255));
                border-radius: 9px;
                border: 1px solid rgba(196,180,140,60);
            }
            QSlider::handle:horizontal:hover {
                background: qradialgradient(cx:0.35, cy:0.35, radius:0.6,
                    stop:0 rgba(240,230,200,255), stop:1 rgba(200,188,150,255));
            }
            QComboBox {
                background: rgba(255,255,255,8);
                color: rgba(255,255,255,220);
                border: 1px solid rgba(196,180,140,40);
                border-radius: 8px;
                padding: 6px 12px;
            }
            QComboBox:hover { border-color: rgba(196,180,140,80); }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: rgba(18,20,28,245);
                color: rgba(255,255,255,220);
                border: 1px solid rgba(196,180,140,40);
                border-radius: 8px;
                selection-background-color: rgba(196,180,140,30);
                padding: 4px;
            }
            QLineEdit {
                background: rgba(255,255,255,8);
                color: rgba(255,255,255,220);
                border: 1px solid rgba(196,180,140,40);
                border-radius: 8px;
                padding: 6px 12px;
            }
            QLineEdit:focus { border-color: rgba(196,180,140,100); }
            QScrollArea {
                border: 1px solid rgba(196,180,140,20);
                border-radius: 8px;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(196,180,140,60);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: rgba(196,180,140,90); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QDialogButtonBox QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(196,180,140,40), stop:1 rgba(196,180,140,20));
                color: rgba(196,180,140,240);
                border: 1px solid rgba(196,180,140,60);
                border-radius: 10px;
                padding: 8px 30px;
                font-size: 13px;
                font-weight: bold;
            }
            QDialogButtonBox QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(196,180,140,60), stop:1 rgba(196,180,140,35));
                border-color: rgba(196,180,140,100);
            }
            QDialogButtonBox QPushButton:pressed {
                background: rgba(196,180,140,70);
            }
        """)

        defaults = existing if existing else {
            "name": "自定义",
            "highlight_boost": 120, "saturation_boost": 0, "mid_alpha": 240,
            "dark_factor": 70, "shadow_factor": 30, "specular_size": 25,
            "specular_alpha": 160, "rim_alpha": 15, "hover_rim_alpha": 30,
            "style": "default",
        }
        # Convert float factors to int percentages for sliders
        if existing and existing.get("dark_factor", 0.7) <= 1.0:
            defaults = dict(existing)
            defaults["dark_factor"] = int(defaults.get("dark_factor", 0.7) * 100)
            defaults["shadow_factor"] = int(defaults.get("shadow_factor", 0.3) * 100)
            defaults["specular_size"] = int(defaults.get("specular_size", 0.25) * 100)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit(defaults.get("name", "自定义"))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Preview
        preview_layout = QHBoxLayout()
        preview_layout.addStretch()
        self.preview = SkinPreview()
        preview_layout.addWidget(self.preview)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)

        # Style selector
        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel("风格:"))
        self.style_combo = QComboBox()
        for key, sk in SPHERE_SKINS.items():
            self.style_combo.addItem(sk["name"], key)
        self.style_combo.addItem("自定义", "custom")
        current_style = defaults.get("style", "default")
        idx = self.style_combo.findData(current_style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)
        self.style_combo.currentIndexChanged.connect(self._on_style_changed)
        style_layout.addWidget(self.style_combo)
        layout.addLayout(style_layout)

        # Sliders
        self.sliders = {}
        slider_defs = [
            ("highlight_boost", "高光亮度", 0, 200, defaults.get("highlight_boost", 120)),
            ("saturation_boost", "饱和度", -100, 100, defaults.get("saturation_boost", 0)),
            ("mid_alpha", "中间透明度", 50, 255, defaults.get("mid_alpha", 240)),
            ("dark_factor", "暗部 (%)", 5, 100, defaults.get("dark_factor", 70)),
            ("shadow_factor", "阴影 (%)", 5, 100, defaults.get("shadow_factor", 30)),
            ("specular_size", "高光大小", 5, 50, defaults.get("specular_size", 25)),
            ("specular_alpha", "高光强度", 0, 255, defaults.get("specular_alpha", 160)),
            ("rim_alpha", "边缘光", 0, 150, defaults.get("rim_alpha", 15)),
            ("hover_rim_alpha", "悬停边缘", 0, 200, defaults.get("hover_rim_alpha", 30)),
        ]

        for key, label, mn, mx, val in slider_defs:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(80)
            row.addWidget(lbl)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(mn, mx)
            slider.setValue(val)
            slider.valueChanged.connect(self._on_param_changed)
            row.addWidget(slider)
            val_lbl = QLabel(str(val))
            val_lbl.setFixedWidth(35)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(val_lbl)
            layout.addLayout(row)
            self.sliders[key] = (slider, val_lbl)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._color = QColor(color)
        self._update_preview()

    def _on_style_changed(self):
        style_key = self.style_combo.currentData()
        if style_key in SPHERE_SKINS:
            sk = SPHERE_SKINS[style_key]
            mapping = {
                "highlight_boost": sk.get("highlight_boost", 120),
                "saturation_boost": sk.get("saturation_boost", 0),
                "mid_alpha": sk.get("mid_alpha", 240),
                "dark_factor": int(sk.get("dark_factor", 0.7) * 100),
                "shadow_factor": int(sk.get("shadow_factor", 0.3) * 100),
                "specular_size": int(sk.get("specular_size", 0.25) * 100),
                "specular_alpha": sk.get("specular_alpha", 160),
                "rim_alpha": sk.get("rim_alpha", 15),
                "hover_rim_alpha": sk.get("hover_rim_alpha", 30),
            }
            for key, val in mapping.items():
                if key in self.sliders:
                    self.sliders[key][0].blockSignals(True)
                    self.sliders[key][0].setValue(val)
                    self.sliders[key][0].blockSignals(False)
                    self.sliders[key][1].setText(str(val))
            self._update_preview()

    def _on_param_changed(self):
        for key, (slider, lbl) in self.sliders.items():
            lbl.setText(str(slider.value()))
        # Switch style to "custom" if user manually adjusts
        idx = self.style_combo.findData("custom")
        if idx >= 0 and self.style_combo.currentData() != "custom":
            self.style_combo.blockSignals(True)
            self.style_combo.setCurrentIndex(idx)
            self.style_combo.blockSignals(False)
        self._update_preview()

    def _update_preview(self):
        skin = self.get_skin_data()
        self.preview.update_skin(skin, self._color)

    def get_skin_data(self):
        sv = {key: slider.value() for key, (slider, _) in self.sliders.items()}
        return {
            "name": self.name_edit.text().strip() or "自定义",
            "highlight_boost": sv["highlight_boost"],
            "saturation_boost": sv["saturation_boost"],
            "mid_alpha": sv["mid_alpha"],
            "dark_factor": sv["dark_factor"] / 100.0,
            "shadow_factor": sv["shadow_factor"] / 100.0,
            "specular_size": sv["specular_size"] / 100.0,
            "specular_alpha": sv["specular_alpha"],
            "rim_alpha": sv["rim_alpha"],
            "hover_rim_alpha": sv["hover_rim_alpha"],
            "style": self.style_combo.currentData() if self.style_combo.currentData() != "custom" else "default",
        }


class _AppRulesDialog(QDialog):
    """Dialog to configure per-application pause/run rules."""
    STYLE = """
        QDialog { background: rgba(22,24,34,255); color: white;
                  border: 1px solid rgba(196,180,140,40); border-radius: 12px; }
        QLabel  { color: rgba(255,255,255,200); }
        QPushButton { background: rgba(196,180,140,40); color: white;
                      border: 1px solid rgba(196,180,140,60); border-radius: 6px;
                      padding: 6px 14px; }
        QPushButton:hover { background: rgba(196,180,140,70); }
        QListWidget { background: rgba(30,32,44,200); color: white;
                      border: 1px solid rgba(196,180,140,30); border-radius: 6px; }
        QListWidget::item:selected { background: rgba(196,180,140,50); }
        QComboBox { background: rgba(40,42,54,200); color: white;
                    border: 1px solid rgba(196,180,140,40); border-radius: 6px; padding: 4px 8px; }
        QLineEdit { background: rgba(40,42,54,200); color: white;
                    border: 1px solid rgba(196,180,140,40); border-radius: 6px; padding: 6px; }
    """

    def __init__(self, rules, parent=None):
        super().__init__(parent)
        self.setWindowTitle("应用程序规则")
        self.setMinimumSize(500, 380)
        self.rules = [dict(r) for r in rules]  # deep copy
        try:
            self.setStyleSheet(self.STYLE)
        except Exception:
            pass
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        info = QLabel("当以下应用程序运行时，覆盖全局回放设置：")
        info.setStyleSheet("color: rgba(255,255,255,140); font-size: 12px;")
        lay.addWidget(info)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        lay.addWidget(self._list, 1)

        # Edit area
        edit_row = QHBoxLayout()
        edit_row.addWidget(QLabel("进程名："))
        self._exe_edit = QLineEdit()
        self._exe_edit.setPlaceholderText("例: chrome.exe")
        edit_row.addWidget(self._exe_edit, 1)
        edit_row.addWidget(QLabel("行为："))
        self._behavior_combo = QComboBox()
        self._behavior_combo.addItems(["暂停", "保持运行"])
        edit_row.addWidget(self._behavior_combo)
        lay.addLayout(edit_row)

        # Buttons
        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕ 添加")
        add_btn.clicked.connect(self._add_rule)
        btn_row.addWidget(add_btn)
        del_btn = QPushButton("🗑️ 删除选中")
        del_btn.clicked.connect(self._del_rule)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        lay.addLayout(btn_row)

    def _refresh_list(self):
        self._list.clear()
        for r in self.rules:
            beh = "暂停" if r["behavior"] == "pause" else "保持运行"
            self._list.addItem(f"{r['exe']}  →  {beh}")

    def _on_select(self, row):
        if 0 <= row < len(self.rules):
            r = self.rules[row]
            self._exe_edit.setText(r["exe"])
            self._behavior_combo.setCurrentText("暂停" if r["behavior"] == "pause" else "保持运行")

    def _add_rule(self):
        exe = self._exe_edit.text().strip().lower()
        if not exe:
            return
        # Normalise: ensure .exe suffix for convenience
        if not exe.endswith(".exe"):
            exe += ".exe"
        beh = "pause" if self._behavior_combo.currentText() == "暂停" else "keep_running"
        self.rules.append({"exe": exe, "behavior": beh})
        self._refresh_list()
        self._list.setCurrentRow(len(self.rules) - 1)

    def _del_rule(self):
        row = self._list.currentRow()
        if 0 <= row < len(self.rules):
            self.rules.pop(row)
            self._refresh_list()


class SettingsDialog(QDialog):
    """完整设置对话框 — 回放 / 品质 / 常规 / 关于"""

    SETTINGS_STYLE = """
        QDialog {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(22,24,34,248), stop:1 rgba(14,16,22,248));
            color: rgba(255,255,255,220);
            font-size: 13px;
        }
        QTabWidget::pane {
            border: 1px solid rgba(196,180,140,50);
            border-radius: 6px;
            background: transparent;
            top: -1px;
        }
        QTabBar::tab {
            background: rgba(30,32,42,200);
            color: rgba(255,255,255,140);
            padding: 8px 18px;
            border: 1px solid rgba(196,180,140,30);
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: rgba(50,54,70,220);
            color: rgba(196,180,140,255);
            border-bottom: 2px solid rgba(196,180,140,120);
        }
        QTabBar::tab:hover:!selected {
            background: rgba(40,44,58,200);
        }
        QLabel {
            color: rgba(255,255,255,200);
        }
        QComboBox {
            background: rgba(35,38,50,220);
            color: rgba(255,255,255,220);
            border: 1px solid rgba(196,180,140,60);
            border-radius: 4px;
            padding: 5px 10px;
            min-width: 120px;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        QComboBox::down-arrow {
            width: 0; height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid rgba(196,180,140,180);
        }
        QComboBox QAbstractItemView {
            background: rgba(22,24,34,248);
            color: rgba(255,255,255,220);
            border: 1px solid rgba(196,180,140,50);
            selection-background-color: rgba(196,180,140,60);
        }
        QSlider::groove:horizontal {
            height: 6px;
            background: rgba(40,44,58,200);
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            width: 16px; height: 16px;
            margin: -5px 0;
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #C4B48C, stop:1 #9C886C);
            border-radius: 8px;
        }
        QSlider::sub-page:horizontal {
            background: rgba(196,180,140,100);
            border-radius: 3px;
        }
        QRadioButton {
            color: rgba(255,255,255,200);
            spacing: 8px;
        }
        QGroupBox {
            font-weight: bold;
            color: rgba(196,180,140,200);
        }
        QPushButton {
            background: rgba(50,54,70,200);
            color: rgba(255,255,255,200);
            border: 1px solid rgba(196,180,140,60);
            border-radius: 6px;
            padding: 6px 16px;
            min-width: 60px;
        }
        QPushButton:hover {
            background: rgba(60,64,80,220);
            border-color: rgba(196,180,140,100);
        }
        QPushButton:pressed {
            background: rgba(40,44,58,220);
        }
        QDialogButtonBox QPushButton {
            min-width: 80px;
        }
    """

    # 预设配置
    PRESETS = {
        "low":  {"fps": 15, "aa": "none",          "post": False, "tex": "low"},
        "mid":  {"fps": 24, "aa": "none",          "post": True,  "tex": "standard"},
        "high": {"fps": 30, "aa": "msaa_2x",       "post": True,  "tex": "high"},
        "ultra":{"fps": 60, "aa": "msaa_4x",       "post": True,  "tex": "high"},
    }
    AA_TEXT = {"none": "无", "msaa_2x": "MSAA 2x", "msaa_4x": "MSAA 4x"}
    POST_TEXT = {True: "启用", False: "禁用"}
    TEX_TEXT = {"low": "低质量", "standard": "标准", "high": "高质量"}

    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(560, 520)
        try:
            self.setStyleSheet(self.SETTINGS_STYLE)
        except Exception:
            pass

        self._data = dict(data) if data else {}
        self.result_settings = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        tabs = QTabWidget()
        tabs.addTab(self._build_playback_tab(), "回放")
        tabs.addTab(self._build_quality_tab(), "品质")
        tabs.addTab(self._build_general_tab(), "常规")
        tabs.addTab(self._build_about_tab(), "关于")
        layout.addWidget(tabs)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ── 回放标签 ──────────────────────────────────────────────
    def _build_playback_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("▶ 回放")
        header.setStyleSheet("font-size:15px; font-weight:bold; color:rgba(196,180,140,220);")
        layout.addWidget(header)

        self._playback_combos = {}
        rows = [
            ("其他应用程序成为焦点时",  ["暂停", "保持运行"], "暂停",       "wp_focus_behavior"),
            ("其他应用程序最大化时",    ["暂停", "保持运行"], "暂停",       "wp_maximized_behavior"),
            ("其他应用程序全屏时",      ["暂停", "保持运行"], "暂停",       "wp_fullscreen_behavior"),
            ("其他应用程序播放音频时",  ["暂停", "保持运行"], "保持运行",   "wp_audio_behavior"),
            ("显示屏休眠时",            ["暂停", "停止（释放内存）"], "停止（释放内存）", "wp_sleep_behavior"),
            ("笔记本电脑使用电池时",    ["暂停", "保持运行"], "保持运行",   "wp_battery_behavior"),
        ]
        value_map = {"暂停": "pause", "保持运行": "keep_running", "停止（释放内存）": "stop"}
        reverse_map = {v: k for k, v in value_map.items()}

        for label_text, options, default_label, key in rows:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setMinimumWidth(200)
            row.addWidget(lbl)
            combo = QComboBox()
            combo.addItems(options)
            # 设置当前值
            current_val = self._data.get(key)
            if current_val and current_val in reverse_map:
                idx = options.index(reverse_map[current_val])
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText(default_label)
            row.addWidget(combo)
            layout.addLayout(row)
            self._playback_combos[key] = combo

        # 应用程序规则
        row = QHBoxLayout()
        lbl = QLabel("应用程序规则")
        lbl.setMinimumWidth(200)
        row.addWidget(lbl)
        self._app_rules_btn = QPushButton("编辑")
        self._app_rules_btn.clicked.connect(self._edit_app_rules)
        row.addWidget(self._app_rules_btn)
        layout.addLayout(row)

        layout.addStretch()
        return w

    # ── 品质标签 ──────────────────────────────────────────────
    def _build_quality_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("品质")
        layout.addWidget(header)

        # 画质预设
        preset_frame = QFrame()
        preset_frame_layout = QVBoxLayout(preset_frame)
        preset_label = QLabel("画质预设")
        preset_label.setStyleSheet("font-weight: bold; color: rgba(196,180,140,200);")
        preset_frame_layout.addWidget(preset_label)
        preset_row = QHBoxLayout()
        self._preset_btns = {}
        self._preset_group = QButtonGroup(self)
        for i, (key, label) in enumerate([("low", "低"), ("mid", "中"), ("high", "高"), ("ultra", "超高")]):
            btn = QRadioButton(label)
            self._preset_btns[key] = btn
            self._preset_group.addButton(btn, i)
            preset_row.addWidget(btn)
        preset_frame_layout.addLayout(preset_row)
        layout.addWidget(preset_frame)

        # 帧率
        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("帧率："))
        self._fps_slider = QSlider(Qt.Horizontal)
        self._fps_slider.setRange(15, 120)
        self._fps_slider.setValue(self._data.get("target_fps", 30))
        fps_row.addWidget(self._fps_slider)
        self._fps_label = QLabel(str(self._fps_slider.value()))
        self._fps_slider.valueChanged.connect(lambda v: self._fps_label.setText(str(v)))
        self._fps_slider.valueChanged.connect(self._clear_preset_selection)
        fps_row.addWidget(self._fps_label)
        layout.addLayout(fps_row)

        # 抗锯齿
        aa_row = QHBoxLayout()
        aa_row.addWidget(QLabel("抗锯齿："))
        self._aa_combo = QComboBox()
        self._aa_combo.addItems(["无", "MSAA 2x", "MSAA 4x"])
        aa_key = self._data.get("antialiasing", "none")
        aa_reverse = {"none": "无", "msaa_2x": "MSAA 2x", "msaa_4x": "MSAA 4x"}
        self._aa_combo.setCurrentText(aa_reverse.get(aa_key, "无"))
        self._aa_combo.currentIndexChanged.connect(self._clear_preset_selection)
        aa_row.addWidget(self._aa_combo)
        aa_row.addStretch()
        layout.addLayout(aa_row)

        # 后处理
        post_row = QHBoxLayout()
        post_row.addWidget(QLabel("后处理："))
        self._post_combo = QComboBox()
        self._post_combo.addItems(["启用", "禁用"])
        post_val = self._data.get("post_processing", True)
        self._post_combo.setCurrentText("启用" if post_val else "禁用")
        self._post_combo.currentIndexChanged.connect(self._clear_preset_selection)
        post_row.addWidget(self._post_combo)
        post_row.addStretch()
        layout.addLayout(post_row)

        # 纹理分辨率
        tex_row = QHBoxLayout()
        tex_row.addWidget(QLabel("纹理分辨率："))
        self._tex_combo = QComboBox()
        self._tex_combo.addItems(["低质量", "标准", "高质量"])
        tex_key = self._data.get("texture_resolution", "high")
        tex_reverse = {"low": "低质量", "standard": "标准", "high": "高质量"}
        self._tex_combo.setCurrentText(tex_reverse.get(tex_key, "高质量"))
        self._tex_combo.currentIndexChanged.connect(self._clear_preset_selection)
        tex_row.addWidget(self._tex_combo)
        tex_row.addStretch()
        layout.addLayout(tex_row)

        layout.addStretch()

        # 延迟应用预设（避免创建时触发信号）
        current_preset = self._data.get("quality_preset", "high")
        if current_preset in self._preset_btns:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda k=current_preset: self._apply_preset(k))

        return w

    def _apply_preset(self, key):
        p = self.PRESETS.get(key)
        if not p:
            return
        self._fps_slider.setValue(p["fps"])
        self._aa_combo.setCurrentText(self.AA_TEXT.get(p["aa"], "无"))
        self._post_combo.setCurrentText("启用" if p["post"] else "禁用")
        self._tex_combo.setCurrentText(self.TEX_TEXT.get(p["tex"], "高质量"))

    def _clear_preset_selection(self):
        self._preset_group.setExclusive(False)
        for btn in self._preset_btns.values():
            btn.setChecked(False)
        self._preset_group.setExclusive(True)

    def _edit_app_rules(self):
        current_rules = self._data.get("app_rules", [])
        dlg = _AppRulesDialog(current_rules, self)
        if dlg.exec_() == QDialog.Accepted:
            self._data["app_rules"] = dlg.rules

    # ── 常规标签 ──────────────────────────────────────────────
    def _build_general_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("常规")
        header.setStyleSheet("font-size:15px; font-weight:bold; color:rgba(196,180,140,220);")
        layout.addWidget(header)

        # ── 球体皮肤 ──
        skin_row = QHBoxLayout()
        skin_lbl = QLabel("球体皮肤：")
        skin_lbl.setMinimumWidth(90)
        skin_row.addWidget(skin_lbl)
        self._skin_combo = QComboBox()
        self._skin_map = {}
        for key, skin in SPHERE_SKINS.items():
            display = skin["name"]
            self._skin_combo.addItem(display)
            self._skin_map[display] = key
        custom_skins = self._data.get("custom_skins", {})
        if custom_skins:
            self._skin_combo.insertSeparator(self._skin_combo.count())
            for cid, cskin in custom_skins.items():
                display = cskin.get("name", cid)
                self._skin_combo.addItem(display)
                self._skin_map[display] = "custom:" + cid
        current_skin = self._data.get("sphere_skin", "default")
        if current_skin.startswith("custom:"):
            cid = current_skin[7:]
            display_name = custom_skins.get(cid, {}).get("name", cid)
        else:
            display_name = SPHERE_SKINS.get(current_skin, {}).get("name", "默认")
        idx = self._skin_combo.findText(display_name)
        if idx >= 0:
            self._skin_combo.setCurrentIndex(idx)
        skin_row.addWidget(self._skin_combo)
        skin_row.addStretch()
        layout.addLayout(skin_row)

        # ── 球体大小 ──
        size_row = QHBoxLayout()
        size_lbl = QLabel("球体大小：")
        size_lbl.setMinimumWidth(90)
        size_row.addWidget(size_lbl)
        self._size_slider = QSlider(Qt.Horizontal)
        self._size_slider.setRange(50, 150)
        current_scale = int(self._data.get("sphere_size_scale", 1.0) * 100)
        self._size_slider.setValue(current_scale)
        self._size_label = QLabel(f"{self._size_slider.value()}%")
        self._size_slider.valueChanged.connect(
            lambda v: self._size_label.setText(f"{v}%"))
        size_row.addWidget(self._size_slider)
        size_row.addWidget(self._size_label)
        layout.addLayout(size_row)

        # ── 不透明度 ──
        opacity_row = QHBoxLayout()
        opacity_lbl = QLabel("不透明度：")
        opacity_lbl.setMinimumWidth(90)
        opacity_row.addWidget(opacity_lbl)
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(20, 100)
        current_opacity = int(self._data.get("window_opacity", 100))
        self._opacity_slider.setValue(current_opacity)
        self._opacity_label = QLabel(f"{self._opacity_slider.value()}%")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%"))
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        layout.addLayout(opacity_row)

        layout.addStretch()
        return w

    # ── 关于标签 ──────────────────────────────────────────────
    def _build_about_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(10)

        # Title
        name_lbl = QLabel("桌面收纳")
        name_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: rgba(196,180,140,240);")
        name_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_lbl)

        ver_lbl = QLabel(f"版本 {APP_VERSION}")
        ver_lbl.setStyleSheet("font-size: 13px; color: rgba(255,255,255,140);")
        ver_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver_lbl)

        desc_lbl = QLabel("一款现代化的桌面组织工具，支持动态壁纸效果。")
        desc_lbl.setStyleSheet("font-size: 13px; color: rgba(255,255,255,160);")
        desc_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_lbl)

        layout.addSpacing(12)

        # Feature highlights
        features = QLabel(
            "· 3D 旋转球环，直观展示分类\n"
            "· 壁纸模式，浮于桌面之上\n"
            "· 多显示器支持\n"
            "· 动态壁纸（图片/视频/粒子/渐变）\n"
            "· 应用程序规则，智能暂停策略\n"
            "· 全局热键 Ctrl+Shift+O\n"
            "· 开机自启、系统托盘"
        )
        features.setStyleSheet("color: rgba(255,255,255,160); font-size: 12px; line-height: 1.6;")
        features.setAlignment(Qt.AlignCenter)
        layout.addWidget(features)

        layout.addSpacing(12)

        # Keyboard shortcuts reference
        shortcuts = QLabel(
            "<b style='color: rgba(196,180,140,200);'>快捷键</b><br>"
            "<span style='color: rgba(255,255,255,140); font-size: 12px;'>"
            "Ctrl+Shift+O　　全局显示/隐藏<br>"
            "Ctrl+N　　　　　新建分类<br>"
            "Ctrl+O　　　　　打开设置<br>"
            "Ctrl+E　　　　　显示/隐藏窗口<br>"
            "ESC　　　　　　 关闭菜单/退出移动模式"
            "</span>"
        )
        shortcuts.setTextFormat(Qt.RichText)
        shortcuts.setStyleSheet("background: rgba(30,32,44,180); padding: 10px 16px; border-radius: 8px;")
        layout.addWidget(shortcuts)

        layout.addStretch()
        return w

    # ── 结果输出 ──────────────────────────────────────────────
    def _on_accept(self):
        # 收集回放设置
        value_map = {"暂停": "pause", "保持运行": "keep_running", "停止（释放内存）": "stop"}
        for key, combo in self._playback_combos.items():
            self.result_settings[key] = value_map.get(combo.currentText(), "keep_running")

        # 收集品质设置
        # 找到当前选中的预设
        checked_btn = self._preset_group.checkedButton()
        preset_key = None
        for k, btn in self._preset_btns.items():
            if btn.isChecked():
                preset_key = k
                break
        self.result_settings["quality_preset"] = preset_key or "custom"
        self.result_settings["target_fps"] = self._fps_slider.value()

        aa_reverse = {v: k for k, v in self.AA_TEXT.items()}
        self.result_settings["antialiasing"] = aa_reverse.get(self._aa_combo.currentText(), "none")
        self.result_settings["post_processing"] = self._post_combo.currentText() == "启用"
        tex_reverse = {v: k for k, v in self.TEX_TEXT.items()}
        self.result_settings["texture_resolution"] = tex_reverse.get(self._tex_combo.currentText(), "high")

        # 收集常规设置
        skin_display = self._skin_combo.currentText()
        self.result_settings["sphere_skin"] = self._skin_map.get(skin_display, "default")
        self.result_settings["sphere_size_scale"] = self._size_slider.value() / 100.0
        self.result_settings["window_opacity"] = self._opacity_slider.value()

        # 收集应用程序规则
        if "app_rules" in self._data:
            self.result_settings["app_rules"] = self._data["app_rules"]

        # 清理旧 boolean 键
        for old_key in ["wp_pause_on_focus_loss", "wp_pause_on_maximized",
                        "wp_pause_on_fullscreen", "wp_pause_on_sleep"]:
            self.result_settings[old_key] = None  # 标记删除

        self.accept()

    def get_settings(self):
        return self.result_settings


class DesktopOrganizer(QWidget):
    def __init__(self):
        super().__init__()
        self.data = self._load_data()
        self._radial_menu = None
        self._wallpaper_mode = False
        self._timers_paused = False
        self._prev_snapshot = self._take_snapshot()
        # 壁纸引擎
        self._wallpaper = WallpaperManager(self)
        self._wallpaper.restore_state(self.data.get("wallpaper"))
        self._wallpaper.wallpaper_changed.connect(self._on_wallpaper_changed)
        self._setup_window()
        self._setup_ui()
        # 应用启动设置
        self.circle_area._size_scale = self.data.get("sphere_size_scale", 1.0)
        opacity = self.data.get("window_opacity", 100)
        self.setWindowOpacity(opacity / 100.0)
        # 注册全局热键
        QTimer.singleShot(1000, self._register_hotkey)
        # 静默检查更新（延迟5秒）
        QTimer.singleShot(5000, self._check_update_silent)

    def _load_data(self):
        data = None
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        if data is None:
            data = json.loads(json.dumps(DEFAULT_DATA))

        # 迁移旧 boolean 键到新 string 键
        migration = {
            "wp_pause_on_focus_loss": ("wp_focus_behavior", True),
            "wp_pause_on_maximized": ("wp_maximized_behavior", True),
            "wp_pause_on_fullscreen": ("wp_fullscreen_behavior", True),
            "wp_pause_on_sleep": ("wp_sleep_behavior", True),
        }
        for old_key, (new_key, default_bool) in migration.items():
            if old_key in data and new_key not in data:
                data[new_key] = "pause" if data[old_key] else "keep_running"
                del data[old_key]

        # 迁移绝对路径为相对路径（基于 _BASE_DIR）
        base_str = str(_BASE_DIR)
        for cat in data.get("categories", []):
            for item in cat.get("items", []):
                old_path = item.get("path", "")
                if old_path and os.path.isabs(old_path):
                    try:
                        rel = os.path.relpath(old_path, base_str)
                        if not rel.startswith(".."):
                            item["path"] = rel
                    except (ValueError, OSError):
                        pass

        # 确保新键存在
        data.setdefault("wp_focus_behavior", "pause")
        data.setdefault("wp_maximized_behavior", "pause")
        data.setdefault("wp_fullscreen_behavior", "pause")
        data.setdefault("wp_audio_behavior", "keep_running")
        data.setdefault("wp_sleep_behavior", "stop")
        data.setdefault("wp_battery_behavior", "keep_running")
        data.setdefault("quality_preset", "high")
        data.setdefault("target_fps", 30)
        data.setdefault("antialiasing", "none")
        data.setdefault("post_processing", True)
        data.setdefault("texture_resolution", "high")
        data.setdefault("sphere_size_scale", 1.0)
        data.setdefault("window_opacity", 100)
        data.setdefault("app_rules", [])

        return data

    def _take_snapshot(self):
        """Take a lightweight snapshot of categories for change detection."""
        cats = []
        for c in self.data.get("categories", []):
            items = [{"name": i["name"], "path": i.get("path", "")} for i in c.get("items", [])]
            cats.append({"name": c["name"], "color": c.get("color", ""), "items": items})
        return {"categories": cats, "bg_color": self.data.get("bg_color", ""),
                "bg_image": self.data.get("bg_image", ""), "sphere_skin": self.data.get("sphere_skin", "")}

    def _auto_backup(self):
        """Auto-backup data before destructive operations. Keeps last 5 backups."""
        try:
            backup_dir = _BASE_DIR / "backups"
            backup_dir.mkdir(exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{ts}.json"
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            # Clean old backups (keep last 5)
            backups = sorted(backup_dir.glob("backup_*.json"))
            for old in backups[:-5]:
                old.unlink(missing_ok=True)
        except Exception:
            pass

    def _save_data(self):
        try:
            # Clean up deleted markers
            self.data["categories"] = [c for c in self.data["categories"] if not c.get("_deleted")]
            # Detect changes and log
            new_snapshot = self._take_snapshot()
            changes = self._diff_snapshot(self._prev_snapshot, new_snapshot)
            if changes:
                self._log_changes(changes)
            self._prev_snapshot = new_snapshot
            # Atomic write: write to temp file first, then replace
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(DATA_FILE.parent), suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, str(DATA_FILE))
            except Exception:
                # Cleanup temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            # Auto backup every 10 saves
            if not hasattr(self, '_save_count'):
                self._save_count = 0
            self._save_count += 1
            if self._save_count % 10 == 0:
                self._auto_backup()
        except Exception as e:
            self._log(f"ERROR _save_data: {e}")
            if getattr(self, '_wallpaper_mode', False):
                return
            try:
                QTimer.singleShot(0, lambda: QMessageBox.warning(
                    self, "保存失败",
                    f"设置保存失败，部分更改可能丢失。\n错误: {e}"))
            except Exception:
                pass

    def _diff_snapshot(self, old, new):
        """Compare two snapshots and return a list of change descriptions."""
        diffs = []
        old_cats = {c["name"]: c for c in old.get("categories", [])}
        new_cats = {c["name"]: c for c in new.get("categories", [])}
        # Added categories
        for name in set(new_cats) - set(old_cats):
            diffs.append(f"添加分类「{name}」")
        # Removed categories
        for name in set(old_cats) - set(new_cats):
            diffs.append(f"删除分类「{name}」")
        # Changed categories
        for name in set(old_cats) & set(new_cats):
            oc, nc = old_cats[name], new_cats[name]
            if oc["color"] != nc["color"]:
                diffs.append(f"「{name}」颜色变更")
            old_items = {i["name"] for i in oc["items"]}
            new_items = {i["name"] for i in nc["items"]}
            for item in new_items - old_items:
                diffs.append(f"「{name}」添加项目「{item}」")
            for item in old_items - new_items:
                diffs.append(f"「{name}」删除项目「{item}」")
        # Background
        if old.get("bg_color") != new.get("bg_color"):
            diffs.append("更改背景颜色")
        if old.get("bg_image") != new.get("bg_image"):
            diffs.append("更改背景图片")
        if old.get("sphere_skin") != new.get("sphere_skin"):
            skin_name = new.get("sphere_skin", "默认")
            if skin_name.startswith("custom:"):
                skin_name = "自定义"
            diffs.append(f"更换皮肤「{skin_name}」")
        return diffs

    def _log_changes(self, changes):
        """Append changes to the changelog file."""
        from datetime import datetime
        log = []
        if CHANGELOG_FILE.exists():
            try:
                with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
                    log = json.load(f)
            except Exception:
                pass
        version = (log[-1]["version"] + 1) if log else 1
        entry = {
            "version": version,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "changes": changes
        }
        log.append(entry)
        # Keep last 200 entries
        if len(log) > 200:
            log = log[-200:]
        with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

    def _setup_window(self):
        self.setWindowTitle("桌面收纳")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None
        self._force_quit = False
        self._wallpaper_mode = False
        self._ui_visible = True  # 标题栏/工具栏是否可见
        self._hover_zone = None  # 'top' / 'bottom' / None
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setMinimumSize(1100, 700)
        self.resize(1500, 900)
        self._setup_tray()

    def _enter_wallpaper_mode(self):
        """进入壁纸模式：全屏透明窗口，球体浮在桌面上"""
        if getattr(self, '_wallpaper_mode', False):
            self._log("已在壁纸模式，跳过重复调用")
            return
        self._wallpaper_mode = True
        self._ui_visible = True
        self.circle_area._wallpaper_mode = True
        self._log("进入壁纸模式")
        # 恢复球环位置
        self._restore_ring_position()
        # 全屏 + 不在任务栏（不置顶）
        screen = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen)
        self.setFixedSize(screen.width(), screen.height())
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.show()
        # 延迟应用桌面层级
        QTimer.singleShot(50, self._apply_desktop_pin)
        # 关键：前台窗口监控 — 检测自己被提到前面就立即推回去
        if not hasattr(self, '_fg_timer'):
            self._fg_timer = QTimer(self)
            self._fg_timer.timeout.connect(self._check_foreground)
        self._fg_timer.start(200)
        # 默认穿透点击
        self._click_through = True
        self._set_click_through(True)
        # 启动鼠标位置检测定时器
        if not hasattr(self, '_hover_timer'):
            self._hover_timer = QTimer(self)
            self._hover_timer.timeout.connect(self._check_hover_for_clickthrough)
        self._hover_timer.start(100)
        # 根据品质设置调整渲染帧率
        target_fps = self.data.get("target_fps", 30)
        interval = max(16, 1000 // target_fps)
        self.circle_area._render_timer.setInterval(interval)
        # 容器完全透明
        self._container.setStyleSheet("QFrame { background: transparent; border: none; }")
        shadow = self._container.graphicsEffect()
        if shadow:
            shadow.setEnabled(False)
        # 圆形区域无边距
        self.layout().setContentsMargins(0, 0, 0, 0)
        # 3秒后自动隐藏UI
        QTimer.singleShot(3000, lambda: self._show_ui(False))
        # 注册屏幕锁定/解锁通知
        try:
            hwnd = int(self.winId())
            WTS_CURRENT_SERVER = 0
            WTS_SESSION_LOCK = 0x7
            WTS_SESSION_UNLOCK = 0x8
            ctypes.windll.wtsapi32.WTSRegisterSessionNotification(hwnd, 0)  # NOTIFY_FOR_ALL_SESSIONS
        except Exception:
            pass
        self.update()

    def _log(self, msg):
        """写日志到文件（缓冲写入，5秒刷新一次）"""
        try:
            if not hasattr(self, '_log_path'):
                self._log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wp_debug.log")
            if not hasattr(self, '_log_buffer'):
                self._log_buffer = []
                self._log_timer = QTimer(self)
                self._log_timer.setSingleShot(True)
                self._log_timer.timeout.connect(self._flush_log)
            import datetime
            ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._log_buffer.append(f"[{ts}] {msg}\n")
            if len(self._log_buffer) >= 20:
                self._flush_log()
            elif not self._log_timer.isActive():
                self._log_timer.start(5000)
        except Exception:
            pass

    def _flush_log(self):
        """将缓冲日志写入文件"""
        try:
            if hasattr(self, '_log_buffer') and self._log_buffer:
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.writelines(self._log_buffer)
                self._log_buffer.clear()
        except Exception:
            pass

    def _check_foreground(self):
        """检测前台窗口 — 如果自己被提到前面，立即推回去"""
        if not getattr(self, '_wallpaper_mode', False):
            return
        # 移动模式下检测 ESC 键退出
        if getattr(self.circle_area, '_move_mode', False):
            user32 = ctypes.windll.user32
            VK_ESCAPE = 0x1B
            if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
                self.circle_area._ring_offset_x = self.data.get("ring_offset_x", 0)
                self.circle_area._ring_offset_y = self.data.get("ring_offset_y", 0)
                self.circle_area._update_positions(self.circle_area._btn_entries)
                self._exit_move_mode()
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            fg = user32.GetForegroundWindow()

            # Cache last foreground to skip heavy work when nothing changed
            last_fg = getattr(self, '_last_fg_hwnd', None)
            last_self_ok = getattr(self, '_last_self_ok', True)
            if fg == last_fg and last_self_ok:
                self._check_should_pause()
                return
            self._last_fg_hwnd = fg

            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            HWND_BOTTOM = 1
            # 场景1：自己成了前台窗口
            if fg == hwnd:
                user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                self._last_self_ok = False
            else:
                GW_HWNDNEXT = 2
                top = user32.GetTopWindow(0)
                cur = top
                # 遍历窗口z序，如果我们的窗口不在底层附近就推下去
                found_other = False
                while cur and cur != hwnd:
                    if user32.IsWindowVisible(cur):
                        found_other = True
                        break
                    cur = user32.GetWindow(cur, GW_HWNDNEXT)
                # 我们的窗口不在最底层，且前面有可见窗口 — 正常
                # 如果我们的窗口是顶层可见窗口，推下去
                if cur == hwnd and user32.IsWindowVisible(hwnd):
                    next_wnd = user32.GetWindow(hwnd, GW_HWNDNEXT)
                    if next_wnd and user32.IsWindowVisible(next_wnd):
                        pass  # 前面有窗口，正常
                    else:
                        # 我们在最前面，推下去
                        user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
            self._last_self_ok = True
            # 检查最大化/全屏暂停条件
            self._check_should_pause()
        except Exception:
            pass

    def _exit_wallpaper_mode(self):
        """退出壁纸模式：恢复窗口"""
        if hasattr(self, '_hover_timer'):
            self._hover_timer.stop()
        if hasattr(self, '_fg_timer'):
            self._fg_timer.stop()
        self._click_through = False
        # 从桌面解除嵌入
        try:
            hwnd = int(self.winId())
            ctypes.windll.user32.SetParent(hwnd, 0)
        except Exception:
            pass
        self._wallpaper_mode = False
        self._embed_done = False
        self.circle_area._wallpaper_mode = False
        self._ui_visible = True
        # 恢复窗口标志
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(16777215, 16777215)
        self.setMinimumSize(1100, 700)
        self.resize(1500, 900)
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )
        self.show()
        if hasattr(self, '_title_bar'):
            self._title_bar.show()
        if hasattr(self, '_toolbar'):
            self._toolbar.show()
        if hasattr(self, '_separator'):
            self._separator.show()
        self._apply_container_style()
        shadow = self._container.graphicsEffect()
        if shadow:
            shadow.setEnabled(True)
        self.layout().setContentsMargins(12, 12, 12, 12)
        self.update()

    def _set_click_through(self, enable):
        """设置窗口是否穿透点击"""
        try:
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            base = style | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            if enable:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, base | WS_EX_TRANSPARENT)
            else:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (base & ~WS_EX_TRANSPARENT) & 0xFFFFFFFF)
        except Exception:
            pass

    def _check_hover_for_clickthrough(self):
        """定时检测鼠标是否在球体上，切换点击穿透"""
        if not getattr(self, '_wallpaper_mode', False):
            return
        if getattr(self.circle_area, '_move_mode', False):
            return
        try:
            global_pos = QCursor.pos()
            # Skip if mouse hasn't moved
            if not hasattr(self, '_last_hover_pos'):
                self._last_hover_pos = None
            if global_pos == self._last_hover_pos:
                return
            self._last_hover_pos = global_pos

            local_pos = self.mapFromGlobal(global_pos)
            on_sphere = False
            if hasattr(self, 'circle_area'):
                area = self.circle_area
                for btn, sx, sy, sz, opacity, _ in area._projected:
                    half = sz / 2
                    dx = local_pos.x() - sx
                    dy = local_pos.y() - sy
                    if dx * dx + dy * dy < half * half:
                        on_sphere = True
                        break
                y = local_pos.y()
                if y < 60 or y > self.height() - 80:
                    on_sphere = True

            if on_sphere and self._click_through:
                self._set_click_through(False)
                self._click_through = False
            elif not on_sphere and not self._click_through:
                self._set_click_through(True)
                self._click_through = True
        except Exception:
            pass

    def _toggle_wallpaper_mode(self):
        if self._wallpaper_mode:
            self._exit_wallpaper_mode()
        else:
            self._enter_wallpaper_mode()

    def showEvent(self, event):
        super().showEvent(event)
        if self._is_desktop_pinned():
            QTimer.singleShot(500, self._enter_wallpaper_mode)

    def nativeEvent(self, eventType, message):
        """拦截系统消息：壁纸模式下阻止窗口被激活"""
        if getattr(self, '_wallpaper_mode', False) and eventType == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            WM_ACTIVATE = 0x0006
            WM_MOUSEACTIVATE = 0x0021
            WM_NCACTIVATE = 0x0086
            WM_POWERBROADCAST = 0x0218
            WM_SHOWWINDOW = 0x0018
            WM_WTSSESSION_CHANGE = 0x02B1
            HWND_BOTTOM = 1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010

            if msg.message == WM_ACTIVATE:
                if (msg.wParam & 0xFFFF) != 0:
                    return True, 0
            elif msg.message == WM_MOUSEACTIVATE:
                return True, 3
            elif msg.message == WM_NCACTIVATE and msg.wParam != 0:
                return True, 0
            elif msg.message == WM_POWERBROADCAST:
                PBT_APMRESUMEAUTOMATIC = 0x0012
                PBT_APMSUSPEND = 0x0004
                if msg.wParam == PBT_APMRESUMEAUTOMATIC:
                    self._log("系统唤醒，重新固定桌面")
                    QTimer.singleShot(100, self._apply_desktop_pin)
                    QTimer.singleShot(500, self._apply_desktop_pin)
                    QTimer.singleShot(1500, self._apply_desktop_pin)
                    self._resume_timers()
                elif msg.wParam == PBT_APMSUSPEND:
                    sleep_behavior = self._get_behavior("sleep")
                    if sleep_behavior == "stop":
                        self._stop_wallpaper_resources()
                    elif sleep_behavior == "pause":
                        self._pause_timers()
            elif msg.message == WM_SHOWWINDOW:
                if msg.wParam != 0:
                    hwnd = int(self.winId())
                    ctypes.windll.user32.SetWindowPos(
                        hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
            elif msg.message == WM_WTSSESSION_CHANGE:
                WTS_SESSION_LOCK = 0x7
                WTS_SESSION_UNLOCK = 0x8
                if msg.wParam == WTS_SESSION_LOCK:
                    sleep_behavior = self._get_behavior("sleep")
                    if sleep_behavior == "stop":
                        self._log("屏幕锁定，停止壁纸资源")
                        self._stop_wallpaper_resources()
                    elif sleep_behavior == "pause":
                        self._log("屏幕锁定，暂停定时器")
                        self._pause_timers()
                elif msg.wParam == WTS_SESSION_UNLOCK:
                    self._log("屏幕解锁，恢复定时器")
                    self._resume_timers()
            # 全局热键 Ctrl+Shift+O
            WM_HOTKEY = 0x0312
            if msg.message == WM_HOTKEY and msg.wParam == 1:
                self._toggle_visibility()

        return super().nativeEvent(eventType, message)

    def _pause_timers(self):
        """暂停所有壁纸模式定时器"""
        self._timers_paused = True
        if hasattr(self, '_fg_timer'):
            self._fg_timer.stop()
        if hasattr(self, '_hover_timer'):
            self._hover_timer.stop()
        if hasattr(self, '_circle_area') and hasattr(self._circle_area, '_render_timer'):
            self._circle_area._render_timer.stop()

    def _resume_timers(self):
        """恢复所有壁纸模式定时器"""
        if getattr(self, '_timers_paused', False):
            self._timers_paused = False
            if hasattr(self, '_fg_timer'):
                self._fg_timer.start(200)
            if hasattr(self, '_hover_timer'):
                self._hover_timer.start(100)
            if hasattr(self, '_circle_area') and hasattr(self._circle_area, '_render_timer'):
                self._circle_area._render_timer.start(33)

    @staticmethod
    def _get_exe_name(hwnd):
        """Get the process executable name for a window handle."""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            pid = ctypes.c_uint32()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if not h:
                return ""
            buf = ctypes.create_unicode_buffer(512)
            size = ctypes.c_uint32(512)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                name = os.path.basename(buf.value).lower()
            else:
                name = ""
            kernel32.CloseHandle(h)
            return name
        except Exception:
            return ""

    def _check_should_pause(self):
        """检查是否有最大化/全屏窗口，按性能设置决定是否暂停"""
        if not getattr(self, '_wallpaper_mode', False):
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            fg = user32.GetForegroundWindow()
            if fg == hwnd or fg == 0:
                return

            # 应用程序规则：按 exe 名匹配，优先级高于全局设置
            exe_name = self._get_exe_name(fg)
            app_rules = self.data.get("app_rules", [])
            if exe_name and app_rules:
                for rule in app_rules:
                    rule_exe = rule.get("exe", "").lower()
                    if rule_exe and rule_exe in exe_name:
                        # 命中规则
                        if rule["behavior"] == "pause":
                            if not getattr(self, '_timers_paused', False):
                                self._pause_timers()
                        else:
                            if getattr(self, '_timers_paused', False):
                                self._resume_timers()
                        return

            # 电池检测
            if self._get_behavior("battery") == "pause" and self._is_on_battery():
                if not getattr(self, '_timers_paused', False):
                    self._pause_timers()
                return

            should_pause = False
            # 检查最大化
            if self._get_behavior("maximized") == "pause":
                placement = ctypes.create_string_buffer(44)
                ctypes.memmove(placement, ctypes.c_int(44), 4)
                user32.GetWindowPlacementW(fg, placement)
                show_cmd = struct.unpack_from('i', placement, 8)[0]
                if show_cmd == 3:  # SW_SHOWMAXIMIZED
                    should_pause = True
            # 检查全屏（多显示器感知）
            if not should_pause and self._get_behavior("fullscreen") == "pause":
                rect = ctypes.create_string_buffer(16)
                user32.GetWindowRect(fg, rect)
                l, t, r, b = struct.unpack('iiii', rect.raw)
                # 获取前景窗口所在的显示器
                try:
                    class MONITORINFO(ctypes.Structure):
                        _fields_ = [("cbSize", ctypes.c_uint32),
                                    ("rcMonitor", wintypes.RECT),
                                    ("rcWork", wintypes.RECT),
                                    ("dwFlags", ctypes.c_uint32)]
                    hmon = user32.MonitorFromWindow(fg, 2)  # MONITOR_DEFAULTTONEAREST
                    mi = MONITORINFO()
                    mi.cbSize = ctypes.sizeof(MONITORINFO)
                    if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                        mon_w = mi.rcMonitor.right - mi.rcMonitor.left
                        mon_h = mi.rcMonitor.bottom - mi.rcMonitor.top
                        if (r - l) >= mon_w and (b - t) >= mon_h:
                            should_pause = True
                except Exception:
                    # 回退：用主显示器判断
                    screen = QApplication.primaryScreen().geometry()
                    if (r - l) >= screen.width() and (b - t) >= screen.height():
                        should_pause = True
            if should_pause and not getattr(self, '_timers_paused', False):
                self._pause_timers()
            elif not should_pause and getattr(self, '_timers_paused', False):
                self._resume_timers()
        except Exception:
            pass

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if getattr(self, '_wallpaper_mode', False):
            self._apply_desktop_pin()
            self._resume_timers()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.circle_area._move_mode:
            self.circle_area._ring_offset_x = self.data.get("ring_offset_x", 0)
            self.circle_area._ring_offset_y = self.data.get("ring_offset_y", 0)
            self.circle_area._update_positions(self.circle_area._btn_entries)
            self._exit_move_mode()
        elif event.key() == Qt.Key_Escape and self._radial_menu is not None:
            # ESC 关闭径向菜单
            try:
                self._radial_menu.close()
            except Exception:
                pass
            self._radial_menu = None
        # 非壁纸模式下的快捷键
        if not getattr(self, '_wallpaper_mode', False):
            ctrl = event.modifiers() & Qt.ControlModifier
            if ctrl and event.key() == Qt.Key_N:
                self._add_category()
            elif ctrl and event.key() == Qt.Key_O:
                self._open_settings()
            elif ctrl and event.key() == Qt.Key_E:
                self._toggle_visibility()
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if getattr(self, '_wallpaper_mode', False):
            self._apply_desktop_pin()
            if self._get_behavior("focus") == "pause":
                self._pause_timers()

    def _create_tray_icon(self):
        """Create a simple circular tray icon with warm gold accent."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing, True)
        grad = QRadialGradient(28, 24, 20, 32, 32)
        grad.setColorAt(0, QColor(212, 196, 156))
        grad.setColorAt(0.6, QColor(196, 180, 140))
        grad.setColorAt(1, QColor(140, 128, 96))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawEllipse(8, 8, 48, 48)
        p.setPen(QPen(QColor(255, 248, 230, 100), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(10, 10, 44, 44)
        p.end()
        return QIcon(pixmap)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray_icon = QSystemTrayIcon(self._create_tray_icon(), self)
        self._tray_icon.setToolTip("桌面收纳")
        tray_menu = QMenu()
        tray_menu.setStyleSheet(MENU_STYLE)
        act_show = tray_menu.addAction("显示/隐藏")
        act_show.triggered.connect(self._toggle_visibility)
        tray_menu.addSeparator()
        act_autostart = tray_menu.addAction("开机自启动")
        act_autostart.setCheckable(True)
        act_autostart.setChecked(self._is_autostart_enabled())
        act_autostart.triggered.connect(self._toggle_autostart)
        act_desktop = tray_menu.addAction("固定桌面")
        act_desktop.setCheckable(True)
        act_desktop.setChecked(self._is_desktop_pinned())
        act_desktop.triggered.connect(self._toggle_desktop_pin)
        # 壁纸模式切换
        act_wpmode = tray_menu.addAction("壁纸模式")
        act_wpmode.setCheckable(True)
        act_wpmode.setChecked(False)
        act_wpmode.triggered.connect(lambda checked: self._enter_wallpaper_mode() if checked else self._exit_wallpaper_mode())
        self._act_wpmode = act_wpmode
        # ⚙ 设置
        act_settings = tray_menu.addAction("  ⚙  设置")
        act_settings.triggered.connect(self._open_settings)
        # ↻ 检查更新
        act_update = tray_menu.addAction("  ↻  检查更新")
        act_update.triggered.connect(self._check_update)
        # ✧ 移动球环
        act_move = tray_menu.addAction("  ✧  移动球环")
        act_move.triggered.connect(self._enter_move_mode)
        # 壁纸子菜单
        wp_menu = tray_menu.addMenu("壁纸")
        wp_menu.setStyleSheet(MENU_STYLE)
        act_wp_image = wp_menu.addAction("  ▣  选择图片壁纸...")
        act_wp_image.triggered.connect(self._pick_wallpaper_image)
        act_wp_video = wp_menu.addAction("  ▷  选择视频壁纸...")
        act_wp_video.triggered.connect(self._pick_wallpaper_video)
        wp_menu.addSeparator()
        act_wp_color = wp_menu.addAction("  ●  纯色背景")
        act_wp_color.triggered.connect(self._pick_wallpaper_color)
        act_wp_trans = wp_menu.addAction("  ◌  透明模式")
        act_wp_trans.triggered.connect(self._set_wallpaper_transparent)
        wp_menu.addSeparator()
        act_wp_particles = wp_menu.addAction("  ✦  粒子效果")
        act_wp_particles.triggered.connect(self._set_wallpaper_particles)
        act_wp_gradient = wp_menu.addAction("  ◐  动态渐变")
        act_wp_gradient.triggered.connect(self._set_wallpaper_gradient)
        act_wp_sgradient = wp_menu.addAction("  ◑  静态渐变")
        act_wp_sgradient.triggered.connect(self._pick_wallpaper_gradient)
        tray_menu.addSeparator()
        act_log = tray_menu.addAction("变更日志")
        act_log.triggered.connect(self._show_changelog)
        tray_menu.addSeparator()
        act_export = tray_menu.addAction("  ↗  导出设置")
        act_export.triggered.connect(self._export_settings)
        act_import = tray_menu.addAction("  ↙  导入设置")
        act_import.triggered.connect(self._import_settings)
        tray_menu.addSeparator()
        act_quit = tray_menu.addAction("退出")
        act_quit.triggered.connect(self._quit_app)
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _toggle_visibility(self):
        if self.isVisible():
            if self._radial_menu is not None:
                try:
                    self._radial_menu.close()
                except Exception:
                    pass
                self._radial_menu = None
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def _show_changelog(self):
        """Show changelog in a dialog."""
        log = []
        if CHANGELOG_FILE.exists():
            try:
                with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
                    log = json.load(f)
            except Exception:
                pass
        if not log:
            QMessageBox.information(self, "变更日志", "暂无变更记录。")
            return
        # Build text
        lines = []
        for entry in reversed(log[-50:]):  # show last 50
            lines.append(f"[v{entry['version']}]  {entry['time']}")
            for ch in entry["changes"]:
                lines.append(f"    • {ch}")
            lines.append("")
        dlg = QDialog(self)
        dlg.setWindowTitle("变更日志")
        dlg.setMinimumSize(420, 500)
        dlg.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22,24,34,255), stop:1 rgba(14,16,22,255));
                color: white;
                border: 1px solid rgba(196,180,140,40);
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n".join(lines))
        text.setStyleSheet("""
            QTextEdit {
                background: rgba(0,0,0,30);
                color: rgba(255,255,255,200);
                border: 1px solid rgba(196,180,140,25);
                border-radius: 8px;
                padding: 8px;
                font-family: 'Microsoft YaHei';
                font-size: 12px;
            }
        """)
        layout.addWidget(text)
        btn = QPushButton("关闭")
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(196,180,140,40), stop:1 rgba(196,180,140,20));
                color: rgba(196,180,140,240);
                border: 1px solid rgba(196,180,140,60);
                border-radius: 10px;
                padding: 8px 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(196,180,140,60), stop:1 rgba(196,180,140,35));
            }
        """)
        btn.clicked.connect(dlg.close)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        dlg.exec_()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visibility()

    _REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    _APP_NAME = "DesktopOrganizer"

    def _is_autostart_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._REG_KEY, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, self._APP_NAME)
            winreg.CloseKey(key)
            return bool(val)
        except Exception:
            return False

    def _toggle_autostart(self, checked):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._REG_KEY, 0, winreg.KEY_SET_VALUE)
            if checked:
                if getattr(sys, 'frozen', False):
                    cmd = f'"{sys.executable}"'
                else:
                    exe = sys.executable
                    script = os.path.abspath(sys.argv[0])
                    cmd = f'"{exe}" "{script}"'
                winreg.SetValueEx(key, self._APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, self._APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass

    def _is_desktop_pinned(self):
        return self.data.get("desktop_pinned", True)

    def _toggle_desktop_pin(self, checked):
        self.data["desktop_pinned"] = checked
        self._save_data()
        self._apply_desktop_pin()

    def _open_settings(self):
        """打开设置对话框"""
        try:
            # 壁纸模式下临时隐藏整个窗口，只显示设置对话框
            was_wallpaper = getattr(self, '_wallpaper_mode', False)
            if was_wallpaper:
                self.hide()
                try:
                    hwnd = int(self.winId())
                    GWL_EXSTYLE = -20
                    WS_EX_NOACTIVATE = 0x08000000
                    WS_EX_TRANSPARENT = 0x00000020
                    user32 = ctypes.windll.user32
                    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    ex = ex & ~WS_EX_NOACTIVATE & ~WS_EX_TRANSPARENT
                    ex &= 0xFFFFFFFF
                    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
                except Exception:
                    pass

            dialog = SettingsDialog(self, data=self.data)
            if dialog.exec_() == QDialog.Accepted:
                settings = dialog.get_settings()
                keys_to_remove = [k for k, v in settings.items() if v is None]
                for k in keys_to_remove:
                    self.data.pop(k, None)
                    settings.pop(k, None)
                self.data.update(settings)
                self._save_data()
                # 应用常规设置
                skin_key = self.data.get("sphere_skin", "default")
                CategoryCircleButton.current_skin = skin_key
                if skin_key.startswith("custom:"):
                    cid = skin_key[7:]
                    CategoryCircleButton._custom_skin_data = self.data.get("custom_skins", {}).get(cid)
                self.circle_area._size_scale = self.data.get("sphere_size_scale", 1.0)
                self.circle_area.update()
                opacity = self.data.get("window_opacity", 100)
                self.setWindowOpacity(opacity / 100.0)
                # 应用品质设置: 帧率 (实时生效)
                target_fps = self.data.get("target_fps", 30)
                interval = max(16, 1000 // target_fps)
                self.circle_area._render_timer.setInterval(interval)
        except Exception as e:
            import traceback
            self._log(f"ERROR _open_settings: {e}\n{traceback.format_exc()}")
        finally:
            # 恢复壁纸模式的窗口标志
            if was_wallpaper:
                try:
                    hwnd = int(self.winId())
                    GWL_EXSTYLE = -20
                    WS_EX_NOACTIVATE = 0x08000000
                    WS_EX_TRANSPARENT = 0x00000020
                    user32 = ctypes.windll.user32
                    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    ex = ex | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT
                    ex &= 0xFFFFFFFF
                    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
                    self._click_through = True
                    # 恢复整个窗口显示
                    self.show()
                except Exception:
                    pass

    def _enter_move_mode(self):
        """进入/退出移动球环模式"""
        if not getattr(self, '_wallpaper_mode', False):
            QMessageBox.information(self, "提示", "请先开启壁纸模式")
            return
        # 已经在移动模式 → 保存位置并退出
        if self.circle_area._move_mode:
            self._exit_move_mode()
            return
        self.circle_area._move_mode = True
        self.circle_area.setCursor(Qt.SizeAllCursor)
        self._set_click_through(False)
        self._click_through = False
        # 显示操作提示
        self._show_move_hint(True)

    def _exit_move_mode(self):
        """退出移动球环模式"""
        self.circle_area._move_mode = False
        self.circle_area.setCursor(Qt.ArrowCursor)
        self._set_click_through(True)
        self._click_through = True
        self._save_ring_position()
        self._show_move_hint(False)

    def _show_move_hint(self, show):
        """显示/隐藏移动模式操作提示"""
        if show:
            if not hasattr(self, '_move_hint_label'):
                from PyQt5.QtWidgets import QLabel
                self._move_hint_label = QLabel(
                    "拖拽移动球环位置  |  按 ESC 或右键托盘退出移动模式",
                    self)
                self._move_hint_label.setStyleSheet(
                    "background: rgba(0,0,0,180); color: white; "
                    "padding: 10px 20px; border-radius: 8px; font-size: 14px;")
                self._move_hint_label.setAlignment(Qt.AlignCenter)
                self._move_hint_label.setFixedHeight(44)
            # 放在窗口底部居中
            hint = self._move_hint_label
            hint.show()
            hint.adjustSize()
            hint.move(
                (self.width() - hint.width()) // 2,
                self.height() - hint.height() - 30)
            # 5秒后自动隐藏
            QTimer.singleShot(5000, lambda: self._show_move_hint(False))
        else:
            if hasattr(self, '_move_hint_label'):
                self._move_hint_label.hide()

    def _save_ring_position(self):
        """保存球环位置到数据文件"""
        ox = self.circle_area._ring_offset_x
        oy = self.circle_area._ring_offset_y
        self.data["ring_offset_x"] = int(ox)
        self.data["ring_offset_y"] = int(oy)
        self._save_data()

    def _restore_ring_position(self):
        """启动时恢复球环位置"""
        self.circle_area._ring_offset_x = self.data.get("ring_offset_x", 0)
        self.circle_area._ring_offset_y = self.data.get("ring_offset_y", 0)
        self.circle_area._update_positions(self.circle_area._btn_entries)

    def _get_behavior(self, trigger_key):
        """统一行为查找：返回 'pause' / 'keep_running' / 'stop'"""
        key_map = {
            "focus": "wp_focus_behavior",
            "maximized": "wp_maximized_behavior",
            "fullscreen": "wp_fullscreen_behavior",
            "audio": "wp_audio_behavior",
            "sleep": "wp_sleep_behavior",
            "battery": "wp_battery_behavior",
        }
        new_key = key_map.get(trigger_key, "")
        val = self.data.get(new_key)
        if val is not None:
            return val
        # 兼容旧 boolean 键
        old_map = {
            "focus": "wp_pause_on_focus_loss",
            "maximized": "wp_pause_on_maximized",
            "fullscreen": "wp_pause_on_fullscreen",
            "sleep": "wp_pause_on_sleep",
        }
        old_key = old_map.get(trigger_key, "")
        if old_key and old_key in self.data:
            return "pause" if self.data[old_key] else "keep_running"
        defaults = {
            "focus": "pause", "maximized": "pause", "fullscreen": "pause",
            "audio": "keep_running", "sleep": "stop", "battery": "keep_running",
        }
        return defaults.get(trigger_key, "keep_running")

    def _stop_wallpaper_resources(self):
        """停止定时器并释放壁纸资源（释放内存）"""
        self._pause_timers()

    def _is_on_battery(self):
        """检测是否使用电池供电"""
        try:
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_ubyte),
                    ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte),
                    ("Reserved1", ctypes.c_ubyte),
                    ("BatteryLifeTime", ctypes.c_uint32),
                    ("BatteryFullLifetime", ctypes.c_uint32),
                ]
            status = SYSTEM_POWER_STATUS()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
            return status.ACLineStatus == 0
        except Exception:
            return False

    def _apply_desktop_pin(self):
        """把窗口放到桌面层"""
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32

            # 第一次调用：设置扩展样式
            if not getattr(self, '_embed_done', False):
                GWL_EXSTYLE = -20
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_NOACTIVATE = 0x08000000
                WS_EX_LAYERED = 0x00080000
                WS_EX_TRANSPARENT = 0x00000020
                current_ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                has_transparent = bool(current_ex & WS_EX_TRANSPARENT)
                new_ex = current_ex | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED
                if has_transparent:
                    new_ex |= WS_EX_TRANSPARENT
                new_ex &= 0xFFFFFFFF
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_ex)
                self._embed_done = True
                self._log(f"扩展样式设置完成 ex=0x{user32.GetWindowLongW(hwnd, GWL_EXSTYLE):X}")

            # 每次调用：HWND_BOTTOM 保底
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            HWND_BOTTOM = 1
            user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        except Exception as e:
            self._log(f"ERROR _apply_desktop_pin: {e}")

    def _keep_on_bottom(self):
        self._apply_desktop_pin()

    def _quit_app(self):
        self._unregister_hotkey()
        self._force_quit = True
        self._flush_log()
        # 保存壁纸状态
        self.data["wallpaper"] = self._wallpaper.get_state()
        self._wallpaper.cleanup()
        self._save_data()
        self._tray_icon.hide()
        QApplication.quit()

    def _check_update(self):
        """检查 GitHub 上是否有新版本"""
        self._do_check_update(show_msg=True)

    def _check_update_silent(self):
        """静默检查更新（启动时调用）"""
        self._do_check_update(show_msg=False)

    def _do_check_update(self, show_msg=False):
        """统一的更新检查逻辑"""
        from PyQt5.QtCore import QThread, pyqtSignal

        class _UpdateChecker(QThread):
            finished = pyqtSignal(str, str)

            def run(self):
                try:
                    import urllib.request
                    import json as _json
                    url = "https://api.github.com/repos/luck-l6/aurora/releases/latest"
                    req = urllib.request.Request(url, headers={"User-Agent": "DesktopOrganizer"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = _json.loads(resp.read().decode())
                        tag = data.get("tag_name", "")
                        html_url = data.get("html_url", "")
                        self.finished.emit(tag, html_url)
                except Exception:
                    self.finished.emit("", "")

        def _strip_v(ver):
            """Safely remove leading 'v' prefix."""
            return ver[1:] if ver.startswith("v") else ver

        def on_check_done(latest, url):
            if not latest:
                if show_msg:
                    QMessageBox.information(self, "检查更新", "无法检查更新，请检查网络连接。")
                return
            current = _strip_v(APP_VERSION)
            if _strip_v(latest) != current:
                if show_msg:
                    reply = QMessageBox.information(
                        self, "发现新版本",
                        f"当前版本: v{current}\n最新版本: {latest}\n\n是否打开下载页面？",
                        QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes and url:
                        import webbrowser
                        webbrowser.open(url)
                else:
                    self._tray_icon.showMessage(
                        "发现新版本",
                        f"v{current} → {latest}\n右键托盘 → 检查更新 查看详情",
                        QSystemTrayIcon.Information, 5000)
            elif show_msg:
                QMessageBox.information(self, "检查更新", f"当前已是最新版本 v{current}")

        # Finish old thread before starting new one
        if hasattr(self, '_update_thread') and self._update_thread and self._update_thread.isRunning():
            self._update_thread.finished.disconnect()
            self._update_thread.wait(2000)

        self._update_thread = _UpdateChecker()
        self._update_thread.finished.connect(on_check_done)
        self._update_thread.start()

    def _export_settings(self):
        """导出设置到文件"""
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "导出设置", "桌面收纳备份.json",
            "JSON 文件 (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功",
                                    f"设置已导出到:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"错误: {e}")

    def _import_settings(self):
        """从文件导入设置"""
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "导入设置", "",
            "JSON 文件 (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            if "categories" not in new_data:
                QMessageBox.warning(self, "导入失败", "文件格式不正确，缺少 categories 字段。")
                return
            reply = QMessageBox.question(
                self, "确认导入",
                "导入将覆盖当前所有设置和分类数据。\n确定继续吗？",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            self._auto_backup()
            self.data = new_data
            self._save_data()
            self.circle_area.set_buttons(self.data.get("categories", []))
            QMessageBox.information(self, "导入成功", "设置已导入，界面已刷新。")
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"错误: {e}")

    def _register_hotkey(self):
        """注册全局热键 Ctrl+Shift+O 切换显示/隐藏"""
        try:
            user32 = ctypes.windll.user32
            MOD_CONTROL = 0x0002
            MOD_SHIFT = 0x0004
            VK_O = 0x4F
            HOTKEY_ID = 1
            # 先注销旧的
            user32.UnregisterHotKey(int(self.winId()), HOTKEY_ID)
            if not user32.RegisterHotKey(int(self.winId()), HOTKEY_ID,
                                         MOD_CONTROL | MOD_SHIFT, VK_O):
                self._log("全局热键 Ctrl+Shift+O 注册失败（可能被占用）")
            else:
                self._log("全局热键 Ctrl+Shift+O 已注册")
        except Exception as e:
            self._log(f"注册热键失败: {e}")

    def _unregister_hotkey(self):
        """注销全局热键"""
        try:
            user32 = ctypes.windll.user32
            user32.UnregisterHotKey(int(self.winId()), 1)
        except Exception:
            pass

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        # Main container with glass background
        container = QFrame()
        self._container = container
        self._apply_container_style()
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(28, 14, 28, 20)
        c_layout.setSpacing(6)

        # Title bar
        title_bar = QFrame()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet("background: transparent;")
        t_layout = QHBoxLayout(title_bar)
        t_layout.setContentsMargins(4, 0, 4, 0)
        t_layout.setSpacing(14)

        title = QLabel("桌面收纳")
        title.setStyleSheet("""
            color: rgba(255,255,255,235);
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        t_layout.addWidget(title)

        # Category count with refined styling
        count = len([c for c in self.data["categories"] if not c.get("_deleted")])
        count_lbl = QLabel(f"  ·  {count} 个分类")
        count_lbl.setStyleSheet("""
            color: rgba(170,178,195,140);
            font-size: 12px;
            padding-top: 3px;
        """)
        t_layout.addWidget(count_lbl)
        t_layout.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("  搜索分类或应用...")
        self.search_box.setFixedWidth(240)
        self.search_box.setFixedHeight(34)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,12);
                color: rgba(255,255,255,220);
                border: 1px solid rgba(255,255,255,18);
                border-radius: 17px;
                padding-left: 16px;
                padding-right: 12px;
                font-size: 12px;
                selection-background-color: rgba(196,180,140,60);
            }
            QLineEdit:hover {
                border-color: rgba(255,255,255,35);
                background: rgba(255,255,255,18);
            }
            QLineEdit:focus {
                border-color: rgba(196,180,140,120);
                background: rgba(255,255,255,22);
            }
        """)
        self.search_box.textChanged.connect(self._on_search)
        t_layout.addWidget(self.search_box)

        min_btn = QPushButton("—")
        min_btn.setFixedSize(34, 34)
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,100);
                border: none;
                border-radius: 17px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,20);
                color: rgba(255,255,255,220);
            }
        """)
        min_btn.clicked.connect(self.showMinimized)
        t_layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(34, 34)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,100);
                border: none;
                border-radius: 17px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(231,76,60,160);
                color: white;
            }
        """)
        close_btn.clicked.connect(self._save_and_close)
        t_layout.addWidget(close_btn)

        c_layout.addWidget(title_bar)
        self._title_bar = title_bar

        # Circular layout area for category buttons
        self.circle_area = _CircleArea(wallpaper_manager=self._wallpaper)
        skin_key = self.data.get("sphere_skin", "default")
        CategoryCircleButton.current_skin = skin_key
        if skin_key.startswith("custom:"):
            cid = skin_key[7:]
            custom = self.data.get("custom_skins", {}).get(cid)
            if custom:
                CategoryCircleButton._custom_skin_data = custom
        self.circle_area.categoryClicked.connect(self._open_radial)
        self.circle_area.categoryMenuRequested.connect(self._on_category_menu)
        c_layout.addWidget(self.circle_area, 1)

        # Separator with gradient effect
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent,
                stop:0.2 rgba(196,180,140,25),
                stop:0.5 rgba(196,180,140,45),
                stop:0.8 rgba(196,180,140,25),
                stop:1 transparent);
        """)
        c_layout.addWidget(sep)
        self._separator = sep

        # Bottom toolbar with refined styling
        toolbar = QFrame()
        toolbar.setFixedHeight(64)
        toolbar.setStyleSheet("background: transparent;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 6, 0, 0)
        tb_layout.setSpacing(28)
        tb_layout.setAlignment(Qt.AlignCenter)

        btn_add = ToolButton("＋", "新建分类", "#5CB85C")
        btn_add.clicked.connect(self._add_category)
        tb_layout.addWidget(btn_add)

        btn_search = ToolButton("⌕", "搜索", "#4A90D9")
        btn_search.clicked.connect(lambda: self.search_box.setFocus())
        tb_layout.addWidget(btn_search)

        btn_rules = ToolButton("≡", "规则", "#1ABC9C")
        btn_rules.clicked.connect(self._show_rules_dialog)
        tb_layout.addWidget(btn_rules)

        btn_trash = ToolButton("↺", "撤销", "#E8A838")
        btn_trash.clicked.connect(self._show_undo_dialog)
        tb_layout.addWidget(btn_trash)

        btn_bg = ToolButton("◐", "背景", "#9B59B6")
        btn_bg.clicked.connect(self._customize_bg)
        tb_layout.addWidget(btn_bg)

        btn_skin = ToolButton("◎", "球体皮肤", "#E67E22")
        btn_skin.clicked.connect(self._pick_skin)
        tb_layout.addWidget(btn_skin)

        btn_power = ToolButton("⏻", "退出", "#E74C3C")
        btn_power.clicked.connect(self._save_and_close)
        tb_layout.addWidget(btn_power)

        c_layout.addWidget(toolbar)
        self._toolbar = toolbar
        root.addWidget(container)
        self._refresh_list()

    def _on_search(self, text):
        self._refresh_list(text.strip())

    def _refresh_list(self, filter_text=""):
        # Close any open radial menu
        if self._radial_menu:
            self._radial_menu.close()
            self._radial_menu = None

        # Collect visible categories
        visible = []
        for cat in self.data["categories"]:
            if cat.get("_deleted"):
                continue
            if filter_text:
                ft = filter_text.lower()
                cat_match = ft in cat["name"].lower()
                item_match = any(ft in it["name"].lower() for it in cat["items"])
                if not cat_match and not item_match:
                    continue
            visible.append(cat)

        if not visible:
            return

        # Let the 3D sphere handle button creation and animation
        self.circle_area.set_buttons(visible, flyin=True)

    def _open_radial(self, category_data):
        try:
            # Defer creation so the click event finishes first, avoiding UI freeze
            QTimer.singleShot(0, lambda: self._do_open_radial(category_data))
        except Exception:
            self._radial_menu = None

    def _do_open_radial(self, category_data):
        try:
            self._do_open_radial_impl(category_data)
        except Exception:
            self._radial_menu = None

    def _do_open_radial_impl(self, category_data):
        # If a radial is already open, close it first (toggle off)
        if self._radial_menu is not None:
            old = self._radial_menu
            self._radial_menu = None
            try:
                old.close()
            except Exception:
                pass
            return

        # Open radial at the center of the ring, so small spheres surround all big spheres
        ca_w = self.circle_area.width()
        ca_h = self.circle_area.height()
        n_cat = len(self.data.get("categories", []))
        base = min(ca_w, ca_h)
        ring_r = min(240 * n_cat / (2 * math.pi), base * 0.55) if n_cat > 0 else base * 0.40
        orbit_r = int(ring_r + 220)  # orbit outside the big spheres
        center = self.circle_area.mapToGlobal(
            QPoint(ca_w // 2, ca_h // 2))
        self._radial_menu = RadialMenu(category_data, center, orbit_r)
        r = self._radial_menu
        r.closed.connect(lambda r=r: self._on_radial_closed(r))

    def _on_radial_closed(self, radial):
        try:
            if self._radial_menu is radial:
                cat = radial.category_data
                self._radial_menu = None
                if cat.get("_deleted"):
                    self.data["categories"].remove(cat)
                    self._save_data()
                    self._refresh_list(self.search_box.text().strip())
        except Exception:
            self._radial_menu = None

    def _on_category_menu(self, btn):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("重命名", lambda: self._rename_category(btn))
        menu.addAction("更改颜色", lambda: self._change_color(btn))
        menu.addAction("添加项目", lambda: self._add_item(btn))
        menu.addSeparator()
        menu.addAction("删除分类", lambda: self._delete_category(btn))
        menu.exec_(QCursor.pos())

    # ─── Category operations ──────────────────────────────

    def _add_category(self):
        name, ok = QInputDialog.getText(self, "新建分类", "分类名称：")
        if ok and name.strip():
            colors = ["#4A90D9", "#5CB85C", "#E8A838", "#D94A6E",
                       "#9B59B6", "#1ABC9C", "#E67E22", "#3498DB"]
            self.data["categories"].append({
                "name": name.strip(), "color": random.choice(colors), "items": []
            })
            self._refresh_list()
            self._save_data()

    def _delete_category(self, btn):
        reply = QMessageBox.question(self, "确认删除",
            f'确定删除分类 "{btn.category_data["name"]}"？', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._auto_backup()
            self.data["categories"].remove(btn.category_data)
            self._refresh_list()
            self._save_data()

    def _rename_category(self, btn):
        name, ok = QInputDialog.getText(self, "重命名", "新名称：", text=btn.category_data["name"])
        if ok and name.strip():
            btn.category_data["name"] = name.strip()
            self._refresh_list()
            self._save_data()

    def _change_color(self, btn):
        color = QColorDialog.getColor(QColor(btn.category_data["color"]), self, "选择颜色")
        if color.isValid():
            btn.category_data["color"] = color.name()
            self._refresh_list()
            self._save_data()

    def _add_item(self, btn):
        from PyQt5.QtWidgets import QFileDialog
        # 先选文件
        path, _ = QFileDialog.getOpenFileName(
            self, "选择程序", "",
            "可执行文件 (*.exe *.lnk *.bat *.cmd);;所有文件 (*)")
        if not path:
            return
        # 自动用文件名作为项目名
        default_name = Path(path).stem
        name, ok = QInputDialog.getText(self, "添加项目", "项目名称：", text=default_name)
        if ok and name.strip():
            item_name = name.strip()
            current_cat = btn.category_data["name"]
            suggested_cat = self._match_rules(item_name)

            if suggested_cat and suggested_cat != current_cat:
                reply = QMessageBox.question(
                    self, "分类建议",
                    f"「{item_name}」根据规则匹配到分类「{suggested_cat}」\n\n"
                    f"当前正在添加到「{current_cat}」\n是否改为添加到「{suggested_cat}」？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    # Find target category and add there
                    for cat in self.data["categories"]:
                        if cat["name"] == suggested_cat:
                            cat["items"].append({
                                "name": item_name, "path": _to_storage_path(path)
                            })
                            self._auto_backup("添加 {} → {}".format(item_name, suggested_cat))
                            self._refresh_list()
                            self._save_data()
                            return

            btn.category_data["items"].append({
                "name": item_name, "path": _to_storage_path(path)
            })
            self._refresh_list()
            self._save_data()

    def _get_category_names(self):
        """Get list of current category names."""
        return [cat["name"] for cat in self.data["categories"]]

    def _show_rules_dialog(self):
        """Show rules management dialog: add/delete classification rules."""
        existing_names = self._get_category_names()
        rules = self.data.get("app_rules", [])

        dlg = QDialog(self)
        dlg.setWindowTitle("分类规则管理")
        dlg.resize(520, 400)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(dlg)

        # Header
        hdr = QLabel("当文件名包含关键词时，自动建议对应分类")
        hdr.setStyleSheet("color:#888;font-size:12px;padding:4px 0 8px 0;")
        layout.addWidget(hdr)

        # Rules list
        list_widget = QListWidget()
        list_widget.setAlternatingRowColors(True)
        list_widget.setStyleSheet("""
            QListWidget { background:#1e1e2e; border:1px solid #333; border-radius:6px; }
            QListWidget::item { padding:8px 12px; border-bottom:1px solid #2a2a3a; }
            QListWidget::item:hover { background:#2a2a3a; }
        """)
        layout.addWidget(list_widget)

        def refresh_list():
            list_widget.clear()
            nonlocal rules
            rules = self.data.get("app_rules", [])
            for r in rules:
                label = f"「{r['keyword']}」 → {r['category']}"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, r)
                list_widget.addItem(item)

        refresh_list()

        # Add rule section
        add_layout = QHBoxLayout()
        lbl_kw = QLabel("关键词")
        lbl_kw.setStyleSheet("color:#aaa;")
        kw_input = QLineEdit()
        kw_input.setPlaceholderText("如: 微信")
        kw_input.setStyleSheet("padding:6px;background:#2a2a3a;border:1px solid #444;border-radius:4px;")
        lbl_cat = QLabel("→ 分类")
        lbl_cat.setStyleSheet("color:#aaa;")
        cat_combo = QComboBox()
        cat_combo.addItems(existing_names)
        cat_combo.setStyleSheet("padding:6px;background:#2a2a3a;border:1px solid #444;border-radius:4px;")
        btn_add_rule = QPushButton("添加")
        btn_add_rule.setStyleSheet("""
            QPushButton { padding:6px 16px;background:#1ABC9C;color:#fff;border:none;border-radius:4px; }
            QPushButton:hover { background:#16A085; }
        """)

        add_layout.addWidget(lbl_kw)
        add_layout.addWidget(kw_input)
        add_layout.addWidget(lbl_cat)
        add_layout.addWidget(cat_combo)
        add_layout.addWidget(btn_add_rule)
        layout.addLayout(add_layout)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_del = QPushButton("删除选中")
        btn_del.setStyleSheet("""
            QPushButton { padding:6px 16px;background:#E74C3C;color:#fff;border:none;border-radius:4px; }
            QPushButton:hover { background:#C0392B; }
        """)
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet("""
            QPushButton { padding:6px 16px;background:#444;color:#fff;border:none;border-radius:4px; }
            QPushButton:hover { background:#555; }
        """)
        btn_layout.addWidget(btn_del)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        def add_rule():
            kw = kw_input.text().strip()
            if not kw:
                return
            target_cat = cat_combo.currentText()
            if target_cat not in existing_names:
                return
            # Check duplicate
            for r in self.data.get("app_rules", []):
                if r["keyword"] == kw:
                    QMessageBox.information(dlg, "提示", f"关键词「{kw}」已存在规则")
                    return
            rule = {"keyword": kw, "category": target_cat}
            self.data.setdefault("app_rules", []).append(rule)
            self._save_data()
            kw_input.clear()
            refresh_list()

        def delete_rule():
            sel = list_widget.currentItem()
            if not sel:
                return
            rule = sel.data(Qt.UserRole)
            self.data["app_rules"] = [r for r in self.data["app_rules"] if r != rule]
            self._save_data()
            refresh_list()

        btn_add_rule.clicked.connect(add_rule)
        kw_input.returnPressed.connect(add_rule)
        btn_del.clicked.connect(delete_rule)
        btn_close.clicked.connect(dlg.accept)

        dlg.setStyleSheet("""
            QDialog { background:#1a1a2e; color:#ddd; }
            QLabel { color:#ddd; }
            QLineEdit { color:#ddd; }
            QComboBox { color:#ddd; }
        """)
        dlg.exec_()

    def _match_rules(self, item_name):
        """Match an item name against app_rules.
        Returns: category name if matched, None otherwise."""
        item_lower = item_name.lower()
        for rule in self.data.get("app_rules", []):
            if rule["keyword"].lower() in item_lower:
                return rule["category"]
        return None

    def _show_undo_dialog(self):
        """Show undo dialog: restore from auto-backup snapshots."""
        backup_dir = _BASE_DIR / "backups"
        backups = sorted(backup_dir.glob("backup_*.json"), reverse=True)
        if not backups:
            QMessageBox.information(self, "撤销", "暂无备份记录。\n\n备份会在您编辑分类时自动创建。")
            return

        # Parse backup timestamps
        backup_info = []
        for bp in backups:
            ts_raw = bp.stem.replace("backup_", "")
            try:
                dt = time.strptime(ts_raw, "%Y%m%d_%H%M%S")
                label = time.strftime("%m-%d %H:%M", dt)
                backup_info.append((label, ts_raw, bp))
            except ValueError:
                backup_info.append((ts_raw, ts_raw, bp))

        # Count changelog entries after each backup
        changelog = []
        if CHANGELOG_FILE.exists():
            try:
                with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
                    changelog = json.load(f)
            except Exception:
                pass

        def _count_changes_since(backup_ts_str):
            try:
                backup_dt = time.mktime(time.strptime(backup_ts_str, "%Y%m%d_%H%M%S"))
            except ValueError:
                return "?"
            count = 0
            for entry in changelog:
                try:
                    entry_dt = time.mktime(time.strptime(entry["time"], "%Y-%m-%d %H:%M:%S"))
                    if entry_dt > backup_dt:
                        count += 1
                except (ValueError, KeyError):
                    pass
            return count

        # Build dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("撤销更改 — 选择备份")
        dlg.setMinimumWidth(520)
        dlg.setStyleSheet("""
            QDialog { background: rgba(22,24,34,255); color: white; border: 1px solid rgba(196,180,140,40); border-radius: 12px; }
            QLabel { color: rgba(255,255,255,200); }
            QListWidget { background: rgba(40,42,54,200); color: white; border: 1px solid rgba(196,180,140,40); border-radius: 8px; padding: 4px; }
            QListWidget::item { padding: 8px 12px; border-radius: 4px; }
            QListWidget::item:selected { background: rgba(196,180,140,35); }
            QPushButton { background: rgba(196,180,140,40); color: white; border: 1px solid rgba(196,180,140,60); border-radius: 6px; padding: 6px 16px; }
            QPushButton:hover { background: rgba(196,180,140,70); }
        """)
        layout = QVBoxLayout(dlg)

        hint = QLabel("自动备份列表（较新在上）。选择后点击「恢复到此版本」：")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        lst = QListWidget()
        for i, (label, ts_raw, bp) in enumerate(backup_info):
            count = _count_changes_since(ts_raw)
            suffix = f"  — 之后有 {count} 条变更" if count else "  — 最新版本"
            lst.addItem(f"{label}{suffix}")
            if i == 0:
                # Bold hint on first item (latest)
                pass
        layout.addWidget(lst)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(dlg.reject)
        btn_restore = QPushButton("恢复到此版本")
        btn_restore.setStyleSheet("QPushButton { background: rgba(232,168,56,60); } QPushButton:hover { background: rgba(232,168,56,90); }")
        btn_restore.clicked.connect(dlg.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_restore)
        layout.addLayout(btn_layout)

        if dlg.exec_() == QDialog.Rejected:
            return

        idx = lst.currentRow()
        if idx < 0:
            return
        _, _, chosen_bp = backup_info[idx]

        reply = QMessageBox.question(self, "确认撤销",
            f"确定要恢复到 {backup_info[idx][0]} 的备份吗？\n\n"
            f"此操作会丢失该备份之后的所有更改。\n"
            f"当前数据将重新自动备份，不会丢失。",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Save current state as a new backup before restoring
        self._auto_backup()
        try:
            with open(chosen_bp, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            self._save_data()
            self._refresh_list()
            self._restore_ring_position()
            QMessageBox.information(self, "撤销完成",
                f"已恢复到 {backup_info[idx][0]} 的备份。\n\n如需反悔，可再次打开撤销面板选择更早的版本。")
        except Exception as e:
            QMessageBox.warning(self, "恢复失败", f"无法读取备份文件：{e}")

    def _pick_skin(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(14,16,24,240);
                color: rgba(255,255,255,210);
                border: 1px solid rgba(196,180,140,35);
                border-radius: 10px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: rgba(196,180,140,25);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(196,180,140,20);
                margin: 4px 12px;
            }
            QMenu::indicator { width: 16px; height: 16px; }
        """)
        current = self.data.get("sphere_skin", "default")
        # Built-in skins
        for key, skin in SPHERE_SKINS.items():
            action = menu.addAction(skin["name"])
            action.setCheckable(True)
            action.setChecked(key == current)
            action.setData(key)
        # Custom skins
        custom_skins = self.data.get("custom_skins", {})
        if custom_skins:
            menu.addSeparator()
            for cid, cskin in custom_skins.items():
                action = menu.addAction(cskin["name"] + "  ✕")
                action.setCheckable(True)
                action.setChecked(cid == current)
                action.setData("custom:" + cid)
        # Create new
        menu.addSeparator()
        action_new = menu.addAction("＋ 创建自定义皮肤")
        action_new.setData("__create__")

        chosen = menu.exec_(QCursor.pos())
        if not chosen:
            return
        skin_key = chosen.data()
        if skin_key == "__create__":
            self._create_custom_skin()
            return
        # Check if user clicked the ✕ area (right side) to delete
        if skin_key.startswith("custom:"):
            cid = skin_key[7:]
            # Ask: apply or delete?
            reply = QMessageBox.question(self, "自定义皮肤",
                f'应用 "{self.data["custom_skins"][cid]["name"]}" ？\n（点"否"删除此皮肤）',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.data["sphere_skin"] = skin_key
                self._save_data()
                CategoryCircleButton.current_skin = skin_key
                CategoryCircleButton._custom_skin_data = self.data["custom_skins"][cid]
                self.circle_area.update()
            elif reply == QMessageBox.No:
                del self.data["custom_skins"][cid]
                if self.data.get("sphere_skin") == skin_key:
                    self.data["sphere_skin"] = "default"
                    CategoryCircleButton.current_skin = "default"
                self._save_data()
                self.circle_area.update()
            return
        self.data["sphere_skin"] = skin_key
        self._save_data()
        CategoryCircleButton.current_skin = skin_key
        self.circle_area.update()

    def _create_custom_skin(self):
        # Get a representative color from first category
        color = "#4A90D9"
        if self.data.get("categories"):
            color = self.data["categories"][0].get("color", "#4A90D9")
        dlg = CustomSkinDialog(self, existing=None, color=color)
        if dlg.exec_() == QDialog.Accepted:
            skin_data = dlg.get_skin_data()
            cid = "custom_" + str(len(self.data.get("custom_skins", {})) + 1)
            if "custom_skins" not in self.data:
                self.data["custom_skins"] = {}
            self.data["custom_skins"][cid] = skin_data
            skin_key = "custom:" + cid
            self.data["sphere_skin"] = skin_key
            self._save_data()
            CategoryCircleButton.current_skin = skin_key
            CategoryCircleButton._custom_skin_data = skin_data
            self.circle_area.update()

    def _customize_bg(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("选择颜色", self._pick_bg_color)
        menu.addAction("选择图片", self._pick_bg_image)
        menu.addAction("透明背景", self._set_transparent_bg)
        menu.addAction("恢复默认", self._reset_bg)
        menu.exec_(QCursor.pos())

    def _pick_bg_color(self):
        color = QColorDialog.getColor(QColor("#1a1a24"), self, "选择背景颜色")
        if color.isValid():
            self.data["bg_color"] = color.name()
            self._save_data()
            self._apply_container_style()
            self.circle_area.update()

    def _pick_bg_image(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择背景图片", "",
                                               "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.data["bg_image"] = path
            self._save_data()
            self.circle_area._bg_pixmap = QPixmap(path)
            self._apply_container_style()
            self.circle_area.update()

    def _apply_container_style(self):
        bg_color = self.data.get("bg_color", "")
        if bg_color == "transparent":
            self._container.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border-radius: 22px;
                    border: 1px solid rgba(255,255,255,10);
                }
            """)
            shadow = self._container.graphicsEffect()
            if shadow:
                shadow.setEnabled(False)
        else:
            self._container.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0.08, y2:1,
                        stop:0 rgba(16, 18, 26, 245),
                        stop:0.4 rgba(12, 14, 22, 248),
                        stop:1 rgba(8, 10, 16, 252));
                    border-radius: 22px;
                    border: 1px solid rgba(196,180,140,28);
                }
            """)
            shadow = self._container.graphicsEffect()
            if shadow:
                shadow.setEnabled(True)

    def _set_transparent_bg(self):
        self.data["bg_color"] = "transparent"
        self.data.pop("bg_image", None)
        self._save_data()
        self.circle_area._bg_pixmap = None
        self._apply_container_style()
        self.circle_area.update()

    def _on_wallpaper_changed(self):
        """壁纸变化回调，触发重绘"""
        self.circle_area.update()
        # 保存壁纸状态
        self.data["wallpaper"] = self._wallpaper.get_state()
        self._save_data()

    def _pick_wallpaper_image(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择图片壁纸", "",
                                               "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            self._wallpaper.set_image(path)

    def _pick_wallpaper_video(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择视频壁纸", "",
                                               "Videos (*.mp4 *.avi *.mkv *.wmv *.webm)")
        if path:
            self._wallpaper.set_video(path)

    def _pick_wallpaper_color(self):
        color = QColorDialog.getColor(QColor(self._wallpaper.get_color()), self, "选择背景颜色")
        if color.isValid():
            self._wallpaper.set_color(color.name())

    def _set_wallpaper_transparent(self):
        self._wallpaper.set_transparent()

    def _set_wallpaper_particles(self):
        self._wallpaper.set_particles()

    def _set_wallpaper_gradient(self):
        self._wallpaper.set_animated_gradient()

    def _pick_wallpaper_gradient(self):
        """Choose top and bottom colors for static gradient"""
        top = QColorDialog.getColor(QColor("#1a1a2e"), self, "选择渐变顶部颜色")
        if not top.isValid():
            return
        bottom = QColorDialog.getColor(QColor("#0d0d1a"), self, "选择渐变底部颜色")
        if not bottom.isValid():
            return
        self._wallpaper.set_gradient(top.name(), bottom.name())

    def _reset_bg(self):
        self.data.pop("bg_color", None)
        self.data.pop("bg_image", None)
        self._save_data()
        self.circle_area._bg_pixmap = None
        self._apply_container_style()
        self.circle_area.update()

    def _save_and_close(self):
        self._save_data()
        self.close()

    # ─── Window drag & drop ─────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.CopyAction)
            e.acceptProposedAction()

    def dropEvent(self, e):
        e.setDropAction(Qt.CopyAction)
        paths = []
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if p and os.path.exists(p):
                paths.append(p)
        if not paths:
            return

        categories = self.data["categories"]
        if categories:
            names = [c["name"] for c in categories] + ["+ 新建分类"]
            name, ok = QInputDialog.getItem(
                self, "添加到分类", f"将 {len(paths)} 个项目添加到：", names, 0, False)
            if not ok:
                return
            if name == "+ 新建分类":
                name, ok2 = QInputDialog.getText(self, "新建分类", "分类名称：", text="我的应用")
                if not ok2 or not name.strip():
                    return
                colors = ["#4A90D9", "#5CB85C", "#E8A838", "#D94A6E",
                           "#9B59B6", "#1ABC9C", "#E67E22", "#3498DB"]
                cat = {"name": name.strip(), "color": random.choice(colors), "items": []}
                categories.append(cat)
            else:
                cat = next(c for c in categories if c["name"] == name)
        else:
            cat = {"name": "我的应用", "color": random.choice(["#4A90D9", "#5CB85C", "#E8A838"]), "items": []}
            categories.append(cat)

        for p in paths:
            new_path = _move_to_collect(p)
            display = os.path.splitext(os.path.basename(new_path))[0]
            cat["items"].append({"name": display, "path": new_path})

        self._refresh_list()
        self._save_data()

    # ─── Window drag ──────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self._is_desktop_pinned():
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton and not self._is_desktop_pinned():
            self.move(e.globalPos() - self._drag_pos)
        # 壁纸模式下鼠标悬停显示/隐藏UI
        if self._wallpaper_mode:
            y = e.y()
            h = self.height()
            if y < 60:
                self._show_ui(True)
                self._hover_zone = 'top'
            elif y > h - 80:
                self._show_ui(True)
                self._hover_zone = 'bottom'
            elif self._hover_zone:
                self._show_ui(False)
                self._hover_zone = None

    def _show_ui(self, visible):
        """壁纸模式下显示/隐藏标题栏和工具栏"""
        if not self._wallpaper_mode:
            return
        if visible == self._ui_visible:
            return
        self._ui_visible = visible
        if hasattr(self, '_title_bar'):
            self._title_bar.setVisible(visible)
        if hasattr(self, '_toolbar'):
            self._toolbar.setVisible(visible)
        if hasattr(self, '_separator'):
            self._separator.setVisible(visible)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def leaveEvent(self, e):
        """鼠标离开窗口时隐藏UI"""
        if self._wallpaper_mode:
            self._show_ui(False)
            self._hover_zone = None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(50, lambda: self._refresh_list(self.search_box.text().strip()))

    def closeEvent(self, e):
        # 保存壁纸状态
        self.data["wallpaper"] = self._wallpaper.get_state()
        self._save_data()
        # Close radial menu if open
        if self._radial_menu is not None:
            try:
                self._radial_menu.close()
            except Exception:
                pass
            self._radial_menu = None
        # 停止所有壁纸模式定时器
        for timer_name in ('_fg_timer', '_hover_timer'):
            t = getattr(self, timer_name, None)
            if t:
                t.stop()
        self._wallpaper.cleanup()
        if self._force_quit:
            if hasattr(self, '_tray_icon'):
                self._tray_icon.hide()
            super().closeEvent(e)
        else:
            # Hide to tray instead of closing
            e.ignore()
            self.hide()


# ─── Entry Point ──────────────────────────────────────────────────────

def main():
    try:
        # Single instance check
        from PyQt5.QtCore import QSharedMemory
        _shared_mem = QSharedMemory("DesktopOrganizer_SingleInstance_Lock")
        if not _shared_mem.create(1):
            sys.exit(0)
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        font = QFont("Microsoft YaHei", 10)
        app.setFont(font)
        # Global tooltip style
        app.setStyleSheet("""
            QToolTip {
                background: rgba(14,16,24,240);
                color: rgba(255,255,255,210);
                border: 1px solid rgba(196,180,140,40);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QInputDialog, QColorDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(22,24,34,255), stop:1 rgba(14,16,22,255));
                color: white;
                border: 1px solid rgba(196,180,140,40);
                border-radius: 12px;
            }
            QInputDialog QLabel, QColorDialog QLabel {
                color: rgba(255,255,255,220);
            }
            QInputDialog QLineEdit {
                background: rgba(255,255,255,8);
                color: rgba(255,255,255,220);
                border: 1px solid rgba(196,180,140,40);
                border-radius: 8px;
                padding: 6px 12px;
            }
            QInputDialog QLineEdit:focus, QColorDialog QLineEdit:focus {
                border-color: rgba(196,180,140,100);
            }
            QInputDialog QPushButton, QColorDialog QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(196,180,140,40), stop:1 rgba(196,180,140,20));
                color: rgba(196,180,140,240);
                border: 1px solid rgba(196,180,140,60);
                border-radius: 10px;
                padding: 8px 24px;
                font-weight: bold;
            }
            QInputDialog QPushButton:hover, QColorDialog QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(196,180,140,60), stop:1 rgba(196,180,140,35));
                border-color: rgba(196,180,140,100);
            }
        """)
        window = DesktopOrganizer()
        window.show()
        # 启动成功后再隐藏控制台
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except Exception:
            pass
        sys.exit(app.exec_())
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        # Write crash log to file
        try:
            crash_log = str(_BASE_DIR / "crash.log")
            with open(crash_log, "w", encoding="utf-8") as f:
                f.write(f"Error: {e}\n\n{tb_str}")
        except Exception:
            crash_log = None
        # Show error in QMessageBox (visible even when console is hidden)
        try:
            _app = QApplication.instance() or QApplication(sys.argv)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("桌面收纳 - 启动失败")
            msg.setText(f"程序启动时发生错误:\n{e}")
            detail = tb_str
            if crash_log:
                detail += f"\n\n崩溃日志已保存到:\n{crash_log}"
            msg.setDetailedText(detail)
            msg.exec_()
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
