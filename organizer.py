"""Desktop Organizer main application class."""

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
from constants import (
    APP_VERSION, MENU_STYLE, SPHERE_SKINS, DEFAULT_DATA,
    DATA_FILE, CHANGELOG_FILE, COLLECT_DIR, _BASE_DIR,
    CONTAINER_GLASS_STYLE, CONTAINER_TRANSPARENT_STYLE,
    TITLE_STYLE, SUBTITLE_STYLE, SEARCH_STYLE,
    SIDEBAR_STYLE, SIDEBAR_BTN_STYLE,
    WIN_BTN_STYLE, WIN_CLOSE_STYLE, SEPARATOR_STYLE,
    GLASS_TEXT_PRIMARY, GLASS_TEXT_SECONDARY, GLASS_TEXT_DIM,
    GLASS_TOOL_BG, GLASS_TOOL_HOVER, GLASS_TOOL_ACTIVE, GLASS_ACCENT,
    GLASS_SHADOW
)
from icon_utils import (
    _move_to_collect, _resolve_path, _to_storage_path,
    get_icon_pixmap, _extract_icon_pixmap
)
from widgets import (
    AppButton, CategoryCircleButton, RadialMenu,
    CircleArea, ToolButton, SkinPreview
)
from dialogs import SettingsDialog, CustomSkinDialog, AppRulesDialog

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
        # 预加载所有图标（后台）
        QTimer.singleShot(500, self._preload_icons)

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

    def _preload_icons(self):
        """Pre-load all app icons into cache at startup."""
        import threading
        def _worker():
            for cat in self.data.get("categories", []):
                for item in cat.get("items", []):
                    path = item.get("path", "")
                    if path:
                        get_icon_pixmap(path, 48)
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

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
        if hasattr(self, '_sidebar'):
            self._sidebar.show()
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
        act_settings = tray_menu.addAction("⚙ 设置")
        act_settings.triggered.connect(self._open_settings)
        # 🔍 检查更新
        act_update = tray_menu.addAction("🔍 检查更新")
        act_update.triggered.connect(self._check_update)
        # 🖱 移动球环
        act_move = tray_menu.addAction("🖱 移动球环")
        act_move.triggered.connect(self._enter_move_mode)
        # 壁纸子菜单
        wp_menu = tray_menu.addMenu("壁纸")
        wp_menu.setStyleSheet(MENU_STYLE)
        act_wp_image = wp_menu.addAction("📷 选择图片壁纸...")
        act_wp_image.triggered.connect(self._pick_wallpaper_image)
        act_wp_video = wp_menu.addAction("🎬 选择视频壁纸...")
        act_wp_video.triggered.connect(self._pick_wallpaper_video)
        wp_menu.addSeparator()
        act_wp_color = wp_menu.addAction("🎨 纯色背景")
        act_wp_color.triggered.connect(self._pick_wallpaper_color)
        act_wp_trans = wp_menu.addAction("✨ 透明模式")
        act_wp_trans.triggered.connect(self._set_wallpaper_transparent)
        wp_menu.addSeparator()
        act_wp_particles = wp_menu.addAction("✨ 粒子效果")
        act_wp_particles.triggered.connect(self._set_wallpaper_particles)
        act_wp_gradient = wp_menu.addAction("🌈 动态渐变")
        act_wp_gradient.triggered.connect(self._set_wallpaper_gradient)
        act_wp_sgradient = wp_menu.addAction("🎨 静态渐变")
        act_wp_sgradient.triggered.connect(self._pick_wallpaper_gradient)
        tray_menu.addSeparator()
        act_log = tray_menu.addAction("变更日志")
        act_log.triggered.connect(self._show_changelog)
        tray_menu.addSeparator()
        act_export = tray_menu.addAction("📤 导出设置")
        act_export.triggered.connect(self._export_settings)
        act_import = tray_menu.addAction("📥 导入设置")
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
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(28, 16, 28, 16)
        c_layout.setSpacing(6)

        # Title bar
        title_bar = QFrame()
        title_bar.setFixedHeight(56)
        title_bar.setStyleSheet("background: transparent;")
        t_layout = QHBoxLayout(title_bar)
        t_layout.setContentsMargins(4, 0, 4, 0)
        t_layout.setSpacing(14)

        # 主标题 + 副标题竖排
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.setContentsMargins(0, 0, 0, 0)
        title = QLabel("桌面收纳")
        title.setStyleSheet(TITLE_STYLE)
        title_col.addWidget(title)
        count = len([c for c in self.data["categories"] if not c.get("_deleted")])
        total_items = sum(len(c.get("items", [])) for c in self.data["categories"] if not c.get("_deleted"))
        count_lbl = QLabel(f"  {count} 个分类  ·  {total_items} 个应用")
        count_lbl.setStyleSheet(SUBTITLE_STYLE)
        title_col.addWidget(count_lbl)
        t_layout.addLayout(title_col)
        t_layout.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("  搜索分类或应用...")
        self.search_box.setFixedWidth(220)
        self.search_box.setFixedHeight(36)
        self.search_box.setStyleSheet(SEARCH_STYLE)
        self.search_box.textChanged.connect(self._on_search)
        t_layout.addWidget(self.search_box)

        min_btn = QPushButton("—")
        min_btn.setFixedSize(34, 34)
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.setStyleSheet(WIN_BTN_STYLE)
        min_btn.clicked.connect(self.showMinimized)
        t_layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(34, 34)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(WIN_CLOSE_STYLE)
        close_btn.clicked.connect(self._save_and_close)
        t_layout.addWidget(close_btn)

        c_layout.addWidget(title_bar)
        self._title_bar = title_bar

        # Content area: circle_area + right sidebar
        content_row = QHBoxLayout()
        content_row.setSpacing(12)
        content_row.setContentsMargins(0, 0, 0, 0)

        # Circular layout area for category buttons
        self.circle_area = CircleArea(wallpaper_manager=self._wallpaper)
        skin_key = self.data.get("sphere_skin", "default")
        CategoryCircleButton.current_skin = skin_key
        if skin_key.startswith("custom:"):
            cid = skin_key[7:]
            custom = self.data.get("custom_skins", {}).get(cid)
            if custom:
                CategoryCircleButton._custom_skin_data = custom
        self.circle_area.categoryClicked.connect(self._open_radial)
        self.circle_area.categoryMenuRequested.connect(self._on_category_menu)
        content_row.addWidget(self.circle_area, 1)

        # Right sidebar — 液态玻璃胶囊
        sidebar = QFrame()
        sidebar.setFixedWidth(68)
        sidebar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(35,28,18,180),
                    stop:0.5 rgba(25,20,12,200),
                    stop:1 rgba(20,16,10,180));
                border-radius: 32px;
                border: 1px solid rgba(255,255,255,15);
            }
        """)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(9, 20, 9, 20)
        sb_layout.setSpacing(10)
        sb_layout.setAlignment(Qt.AlignCenter)

        # 圆形按钮样式
        circle_btn_style = """
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,180);
                border: 1px solid rgba(255,255,255,15);
                border-radius: 22px;
                font-size: 16px;
                font-family: "Segoe MDL2 Assets", "Segoe UI", sans-serif;
            }
            QPushButton:hover {
                background: rgba(255,255,255,20);
                border-color: rgba(255,255,255,40);
                color: rgba(255,255,255,240);
            }
            QPushButton:checked {
                background: rgba(255,255,255,30);
                border-color: rgba(255,255,255,60);
                color: rgba(255,255,255,255);
            }
        """

        # 5个功能图标按钮
        sidebar_btns = [
            ("O", "球体皮肤", self._pick_skin),
            ("#", "背景", self._customize_bg),
            ("=", "规则", self._show_rules_dialog),
            ("U", "撤销", self._show_undo_dialog),
            ("Q", "搜索", lambda: self.search_box.setFocus()),
        ]
        self._sidebar_btns = []
        for icon, tip, handler in sidebar_btns:
            btn = QPushButton(icon)
            btn.setFixedSize(44, 44)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(circle_btn_style)
            btn.clicked.connect(handler)
            sb_layout.addWidget(btn)
            self._sidebar_btns.append(btn)

        # 分隔线
        sep_line = QFrame()
        sep_line.setFixedSize(24, 1)
        sep_line.setStyleSheet("background: rgba(255,255,255,20); border: none;")
        sb_layout.addWidget(sep_line, alignment=Qt.AlignCenter)

        # 新建分类按钮
        btn_add = QPushButton("+")
        btn_add.setFixedSize(44, 44)
        btn_add.setToolTip("新建分类")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,15);
                color: rgba(255,255,255,200);
                border: 1px solid rgba(255,255,255,20);
                border-radius: 22px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255,255,255,30);
                border-color: rgba(255,255,255,50);
                color: rgba(255,255,255,255);
            }
        """)
        btn_add.clicked.connect(self._add_category)
        sb_layout.addWidget(btn_add)

        sb_layout.addStretch()

        # 底部箭头按钮
        btn_exit = QPushButton(">")
        btn_exit.setFixedSize(44, 44)
        btn_exit.setToolTip("退出")
        btn_exit.setCursor(Qt.PointingHandCursor)
        btn_exit.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,10);
                color: rgba(255,255,255,150);
                border: 1px solid rgba(255,255,255,12);
                border-radius: 22px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(200,80,60,40);
                border-color: rgba(200,80,60,60);
                color: rgba(255,200,180,240);
            }
        """)
        btn_exit.clicked.connect(self._save_and_close)
        sb_layout.addWidget(btn_exit)

        content_row.addWidget(sidebar)
        self._sidebar = sidebar

        c_layout.addLayout(content_row)

        # Separator with gradient effect
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(SEPARATOR_STYLE)
        c_layout.addWidget(sep)
        self._separator = sep

        # Bottom info bar (minimal)
        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(32)
        bottom_bar.setStyleSheet("background: transparent;")
        bb_layout = QHBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(8, 0, 8, 0)
        version_lbl = QLabel(f"v{APP_VERSION}")
        version_lbl.setStyleSheet(f"color: {GLASS_TEXT_DIM}; font-size: 11px;")
        bb_layout.addWidget(version_lbl)
        bb_layout.addStretch()
        c_layout.addWidget(bottom_bar)

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
        # 液态玻璃效果：深色半透明 + 顶部渐变高光
        self._container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(15,12,25,120),
                    stop:0.15 rgba(12,10,20,130),
                    stop:1 rgba(8,6,15,140));
                border-radius: 24px;
                border: 1px solid rgba(255,255,255,20);
            }
        """)
        shadow = self._container.graphicsEffect()
        if shadow:
            shadow.setEnabled(True)
            shadow.setColor(QColor(0, 0, 0, 100))
            shadow.setBlurRadius(45)
            shadow.setOffset(0, 5)

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
        self._force_quit = True
        self._save_data()
        self._wallpaper.cleanup()
        if hasattr(self, '_tray_icon'):
            self._tray_icon.hide()
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().quit()

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
        if hasattr(self, '_sidebar'):
            self._sidebar.setVisible(visible)
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
            e.accept()
            super().closeEvent(e)
        else:
            # Hide to tray instead of closing
            e.ignore()
            self.hide()


