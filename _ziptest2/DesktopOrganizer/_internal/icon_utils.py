"""Icon extraction and path resolution utilities."""

import os
import shutil
import ctypes
from ctypes import wintypes

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QPixmap, QImage, QImageReader

from constants import _BASE_DIR, COLLECT_DIR


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
_gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
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

    # Fast BGRA→RGBA using memoryview + byte swap
    raw = bytearray(buf)
    mv = memoryview(raw)
    # Swap B and R channels in-place
    for i in range(0, len(raw), 4):
        raw[i], raw[i+2] = raw[i+2], raw[i]
        if raw[i+3] == 0 and (raw[i] or raw[i+1] or raw[i+2]):
            raw[i+3] = 255

    if not any(raw):
        return None
    return QPixmap.fromImage(QImage(bytes(raw), size, size, QImage.Format_ARGB32))


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
