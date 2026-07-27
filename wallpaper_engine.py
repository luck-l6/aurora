"""
wallpaper_engine.py — 桌面嵌入 + 壁纸管理模块
WorkerW 桌面嵌入技术 + 图片/视频/纯色壁纸支持
"""
import ctypes
import ctypes.wintypes
import logging
from pathlib import Path

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QSize, QRect, QPointF, Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QRadialGradient, QLinearGradient, QBrush
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QAbstractVideoSurface, QVideoFrame
from PyQt5.QtCore import QUrl

logger = logging.getLogger(__name__)


# ============================================================
#  WorkerW 桌面嵌入
# ============================================================

class WorkerWEmbed:
    """使用 Windows WorkerW 技术将窗口嵌入桌面层"""

    _workerw_hwnd = None

    @staticmethod
    def find_workerw():
        """找到 WorkerW 窗口 — 按优先级尝试多种方式"""
        user32 = ctypes.windll.user32

        progman = user32.FindWindowW("Progman", None)
        if not progman:
            logger.error("未找到 Progman 窗口")
            return None
        logger.info(f"Progman hwnd: {progman}")

        # ── 策略1：Progman 的 WorkerW 子窗口 ──
        # 某些系统上 Progman 已有 WorkerW 子窗口（桌面壁纸层）
        child = user32.FindWindowExW(progman, None, "WorkerW", None)
        if child:
            logger.info(f"策略1成功 — Progman 的 WorkerW 子窗口: {child}")
            WorkerWEmbed._workerw_hwnd = child
            return child

        # ── 策略2：标准方式 — 发送 0x052C 创建分离的 WorkerW ──
        result = ctypes.c_ulong(0)
        user32.SendMessageTimeoutW(
            progman, 0x052C, 0, 0,
            0x0002, 5000, ctypes.byref(result)
        )
        logger.info(f"0x052C result: {result.value}")

        # 再次检查 Progman 的子窗口
        child = user32.FindWindowExW(progman, None, "WorkerW", None)
        if child:
            logger.info(f"策略2成功 — 0x052C 后 Progman 的 WorkerW: {child}")
            WorkerWEmbed._workerw_hwnd = child
            return child

        # ── 策略3：FindWindowExW 遍历顶层 WorkerW ──
        hwnd = user32.FindWindowExW(0, 0, "WorkerW", None)
        workerws = []
        while hwnd:
            shell = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
            workerws.append((hwnd, bool(shell)))
            hwnd = user32.FindWindowExW(0, hwnd, "WorkerW", None)

        logger.info(f"顶层 WorkerW 数量: {len(workerws)}")

        # 找有 SHELLDLL 的 WorkerW，它后面那个是目标
        for i, (wh, has_shell) in enumerate(workerws):
            if has_shell and i + 1 < len(workerws):
                target = workerws[i + 1][0]
                logger.info(f"策略3成功 — SHELLDLL 后的 WorkerW: {target}")
                WorkerWEmbed._workerw_hwnd = target
                return target

        # ── 策略4：EnumWindows 枚举 ──
        enum_workerws = []
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )
        def _enum_cb(hwnd, _):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value == "WorkerW":
                shell = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
                enum_workerws.append((hwnd, bool(shell)))
            return True
        user32.EnumWindows(EnumWindowsProc(_enum_cb), 0)

        for i, (wh, has_shell) in enumerate(enum_workerws):
            if has_shell and i + 1 < len(enum_workerws):
                target = enum_workerws[i + 1][0]
                logger.info(f"策略4成功 — EnumWindows SHELLDLL 后 WorkerW: {target}")
                WorkerWEmbed._workerw_hwnd = target
                return target

        # ── 策略5：任意 WorkerW（第一个） ──
        if workerws:
            logger.info(f"策略5 — 使用第一个顶层 WorkerW: {workerws[0][0]}")
            WorkerWEmbed._workerw_hwnd = workerws[0][0]
            return workerws[0][0]

        if enum_workerws:
            logger.info(f"策略5 — EnumWindows 第一个 WorkerW: {enum_workerws[0][0]}")
            WorkerWEmbed._workerw_hwnd = enum_workerws[0][0]
            return enum_workerws[0][0]

        # ── 策略6：直接用 Progman ──
        logger.info("策略6 — 使用 Progman 本身")
        WorkerWEmbed._workerw_hwnd = progman
        return progman

    @staticmethod
    def embed(hwnd):
        """将窗口嵌入到桌面层"""
        target = WorkerWEmbed.find_workerw()
        if not target:
            logger.error("所有策略均失败，无法嵌入桌面")
            return False
        try:
            user32 = ctypes.windll.user32
            user32.SetParent(hwnd, target)
            logger.info(f"窗口 {hwnd} 已嵌入到 {target}")
            return True
        except Exception as e:
            logger.error(f"嵌入桌面失败: {e}")
            return False

    @staticmethod
    def unembed(hwnd):
        """从桌面层移除窗口，恢复为普通顶层窗口"""
        try:
            ctypes.windll.user32.SetParent(hwnd, 0)
            logger.info(f"窗口 {hwnd} 已从桌面层移除")
            return True
        except Exception as e:
            logger.error(f"移除桌面嵌入失败: {e}")
            return False

    @staticmethod
    def fallback_pin(hwnd):
        """备用方案：HWND_BOTTOM 固定窗口"""
        try:
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            HWND_BOTTOM = 1
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            )
            return True
        except Exception:
            return False


# ============================================================
#  视频帧捕获
# ============================================================

class VideoSurface(QAbstractVideoSurface):
    """自定义视频表面，捕获 QMediaPlayer 的帧"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_frame = QImage()

    def supportedPixelFormats(self, handleType):
        from PyQt5.QtMultimedia import QVideoFrame
        return [QVideoFrame.Format_ARGB32, QVideoFrame.Format_RGB32,
                QVideoFrame.Format_ARGB32_Premultiplied, QVideoFrame.Format_RGB24]

    def present(self, frame):
        if frame.isValid():
            self._current_frame = frame.image()
            # 通知父组件刷新
            if self.parent():
                self.parent()._on_video_frame()
        return True

    def current_frame(self):
        return self._current_frame


# ============================================================
#  粒子效果
# ============================================================

import random
import math

class Particle:
    __slots__ = ['x', 'y', 'vx', 'vy', 'life', 'max_life', 'size', 'color', 'alpha']

    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.5, -0.1)
        self.max_life = random.uniform(200, 600)
        self.life = self.max_life
        self.size = random.uniform(1.5, 4.0)
        # 暖色调粒子
        r = random.randint(180, 255)
        g = random.randint(160, 220)
        b = random.randint(100, 160)
        self.color = QColor(r, g, b)
        self.alpha = 0.0

    def update(self, w, h):
        self.x += self.vx
        self.y += self.vy
        self.vx += random.uniform(-0.02, 0.02)
        self.life -= 1
        # 淡入淡出
        ratio = self.life / self.max_life
        if ratio > 0.8:
            self.alpha = (1.0 - ratio) / 0.2
        elif ratio < 0.2:
            self.alpha = ratio / 0.2
        else:
            self.alpha = 1.0
        return self.life > 0 and 0 <= self.x <= w and 0 <= self.y <= h


class ParticleSystem:
    """浮动粒子背景效果"""

    def __init__(self, count=80):
        self._count = count
        self._w = 1920
        self._h = 1080
        self._particles = []
        self._pool = []  # pre-allocated pool for reuse

    def _spawn_particle(self):
        if self._pool:
            p = self._pool.pop()
            p.__init__(self._w, self._h)
            return p
        return Particle(self._w, self._h)

    def resize(self, w, h):
        self._w, self._h = w, h
        if not self._particles:
            for _ in range(self._count):
                self._particles.append(Particle(w, h))

    def update(self):
        alive = []
        for p in self._particles:
            if p.update(self._w, self._h):
                alive.append(p)
            else:
                self._pool.append(p)
        self._particles = alive
        while len(self._particles) < self._count:
            self._particles.append(self._spawn_particle())

    def paint(self, painter, rect):
        w, h = rect.width(), rect.height()
        self.resize(w, h)
        self.update()
        for p in self._particles:
            painter.setOpacity(p.alpha * 0.6)
            painter.setPen(Qt.NoPen)
            painter.setBrush(p.color)
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
        painter.setOpacity(1.0)


# ============================================================
#  动态渐变背景
# ============================================================

class AnimatedGradient:
    """缓慢移动的渐变背景"""

    def __init__(self):
        self._hue_offset = 0.0
        self._base_color = QColor("#1a1a2e")
        self._accent_color = QColor("#2d1b4e")
        self._speed = 0.1

    def set_colors(self, base, accent):
        self._base_color = QColor(base)
        self._accent_color = QColor(accent)

    def update(self):
        self._hue_offset += self._speed
        if self._hue_offset > 360:
            self._hue_offset -= 360

    def paint(self, painter, rect):
        self.update()
        w, h = rect.width(), rect.height()
        # 底色
        painter.fillRect(rect, self._base_color)
        # 缓慢移动的光晕
        angle = math.radians(self._hue_offset)
        cx = w / 2 + math.cos(angle) * w * 0.3
        cy = h / 2 + math.sin(angle * 0.7) * h * 0.3
        r = max(w, h) * 0.6
        grad = QRadialGradient(cx, cy, r)
        c = self._accent_color
        grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 40))
        grad.setColorAt(0.5, QColor(c.red(), c.green(), c.blue(), 15))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(rect, QBrush(grad))
        # 第二个光晕
        cx2 = w / 2 + math.cos(angle * 1.3 + 2) * w * 0.25
        cy2 = h / 2 + math.sin(angle * 0.5 + 1) * h * 0.25
        grad2 = QRadialGradient(cx2, cy2, r * 0.7)
        grad2.setColorAt(0, QColor(80, 60, 120, 25))
        grad2.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(rect, QBrush(grad2))


# ============================================================
#  壁纸管理器
# ============================================================

class WallpaperManager(QObject):
    """管理壁纸类型：图片 / 视频 / 纯色 / 透明 / 粒子 / 动态渐变"""

    wallpaper_changed = pyqtSignal()

    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_COLOR = "color"
    TYPE_TRANSPARENT = "transparent"
    TYPE_PARTICLES = "particles"
    TYPE_ANIMATED_GRADIENT = "animated_gradient"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._type = self.TYPE_ANIMATED_GRADIENT
        self._color = QColor("#1a1a2e")
        self._image = QImage()
        self._image_path = ""
        self._user_selected = False  # 用户是否手动设置过壁纸

        # 视频播放
        self._player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self._video_surface = VideoSurface(self)
        self._player.setVideoOutput(self._video_surface)
        self._player.setVolume(0)
        self._player.mediaStatusChanged.connect(self._on_media_status)

        # 动态效果
        self._particles = ParticleSystem(80)
        self._animated_gradient = AnimatedGradient()

    # ---------- 设置壁纸 ----------

    def set_image(self, path):
        """设置静态图片壁纸"""
        p = Path(path)
        if not p.exists():
            logger.warning(f"图片不存在: {path}")
            return False
        self._stop_video()
        self._image = QImage(str(p))
        if self._image.isNull():
            logger.warning(f"无法加载图片: {path}")
            return False
        self._type = self.TYPE_IMAGE
        self._image_path = str(p)
        self._user_selected = True
        self.wallpaper_changed.emit()
        logger.info(f"壁纸设为图片: {path}")
        return True

    def set_video(self, path):
        """设置视频壁纸"""
        p = Path(path)
        if not p.exists():
            logger.warning(f"视频不存在: {path}")
            return False
        self._type = self.TYPE_VIDEO
        self._image_path = str(p)
        self._player.setMedia(QMediaContent(QUrl.fromLocalFile(str(p))))
        self._player.play()
        self._user_selected = True
        self.wallpaper_changed.emit()
        logger.info(f"壁纸设为视频: {path}")
        return True

    def set_color(self, color_str):
        """设置纯色壁纸"""
        self._stop_video()
        self._color = QColor(color_str)
        if not self._color.isValid():
            self._color = QColor("#1a1a2e")
        self._type = self.TYPE_COLOR
        self._image_path = ""
        self._user_selected = True
        self.wallpaper_changed.emit()
        logger.info(f"壁纸设为颜色: {color_str}")

    def set_transparent(self):
        """透明模式 — 不绘制背景，显示系统桌面"""
        self._stop_video()
        self._type = self.TYPE_TRANSPARENT
        self._image_path = ""
        self._user_selected = True
        self.wallpaper_changed.emit()
        logger.info("壁纸设为透明")

    def set_particles(self):
        """粒子效果壁纸"""
        self._stop_video()
        self._type = self.TYPE_PARTICLES
        self._image_path = ""
        self._user_selected = True
        self.wallpaper_changed.emit()
        logger.info("壁纸设为粒子效果")

    def set_animated_gradient(self, base="#1a1a2e", accent="#2d1b4e"):
        """动态渐变壁纸"""
        self._stop_video()
        self._animated_gradient.set_colors(base, accent)
        self._type = self.TYPE_ANIMATED_GRADIENT
        self._image_path = ""
        self._user_selected = True
        self.wallpaper_changed.emit()
        logger.info("壁纸设为动态渐变")

    # ---------- 渲染 ----------

    def paint(self, painter, rect):
        """在指定区域绘制壁纸"""
        if self._type == self.TYPE_TRANSPARENT:
            return  # 不绘制任何东西

        if self._type == self.TYPE_COLOR:
            painter.fillRect(rect, self._color)
            return

        if self._type == self.TYPE_IMAGE and not self._image.isNull():
            # 缩放并居中绘制
            scaled = self._image.scaled(
                rect.size(), 1, 1  # KeepAspectRatio, SmoothTransform
            )
            x = rect.x() + (rect.width() - scaled.width()) // 2
            y = rect.y() + (rect.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
            return

        if self._type == self.TYPE_VIDEO:
            frame = self._video_surface.current_frame()
            if not frame.isNull():
                scaled = frame.scaled(
                    rect.size(), 1, 1
                )
                x = rect.x() + (rect.width() - scaled.width()) // 2
                y = rect.y() + (rect.height() - scaled.height()) // 2
                painter.drawImage(x, y, scaled)
            else:
                painter.fillRect(rect, QColor("#000000"))
            return

        if self._type == self.TYPE_PARTICLES:
            painter.fillRect(rect, QColor("#0d0d1a"))
            self._particles.paint(painter, rect)
            return

        if self._type == self.TYPE_ANIMATED_GRADIENT:
            self._animated_gradient.paint(painter, rect)
            return

    # ---------- 状态 ----------

    def get_type(self):
        return self._type

    def get_path(self):
        return self._image_path

    def get_color(self):
        return self._color.name()

    def get_state(self):
        """返回可序列化的状态字典"""
        state = {
            "type": self._type,
            "path": self._image_path,
            "color": self._color.name()
        }
        if self._type == self.TYPE_ANIMATED_GRADIENT:
            state["base_color"] = self._animated_gradient._base_color.name()
            state["accent_color"] = self._animated_gradient._accent_color.name()
        if self._user_selected:
            state["user_selected"] = True
        return state

    def restore_state(self, state):
        """从状态字典恢复壁纸"""
        if not state:
            return
        wp_type = state.get("type", self.TYPE_COLOR)
        # 如果用户没有手动设置过壁纸，保持默认 animated_gradient
        if not state.get("user_selected") and wp_type == self.TYPE_COLOR:
            return
        if wp_type == self.TYPE_IMAGE:
            self.set_image(state.get("path", ""))
        elif wp_type == self.TYPE_VIDEO:
            self.set_video(state.get("path", ""))
        elif wp_type == self.TYPE_TRANSPARENT:
            self.set_transparent()
        elif wp_type == self.TYPE_PARTICLES:
            self.set_particles()
        elif wp_type == self.TYPE_ANIMATED_GRADIENT:
            base = state.get("base_color", "#1a1a2e")
            accent = state.get("accent_color", "#2a1a3e")
            self.set_animated_gradient(base, accent)
        else:
            self.set_color(state.get("color", "#1a1a2e"))

    # ---------- 内部 ----------

    def _stop_video(self):
        self._player.stop()

    def _on_video_frame(self):
        """视频帧更新回调，通知父组件重绘"""
        self.wallpaper_changed.emit()

    def _on_media_status(self, status):
        """视频播放完毕自动循环"""
        from PyQt5.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.EndOfMedia:
            self._player.play()

    def cleanup(self):
        """清理资源"""
        self._stop_video()
        try:
            self._player.deleteLater()
        except Exception:
            pass


# ============================================================
#  调试工具
# ============================================================

def debug_workerw():
    """全面诊断桌面窗口结构"""
    print("=" * 60)
    print("  桌面窗口结构诊断")
    print("=" * 60)
    user32 = ctypes.windll.user32

    def get_class(hwnd):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value

    def get_title(hwnd):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        return buf.value

    def enum_children(parent_hwnd):
        """枚举子窗口"""
        children = []
        child = user32.FindWindowExW(parent_hwnd, None, None, None)
        while child:
            children.append(child)
            child = user32.FindWindowExW(parent_hwnd, child, None, None)
        return children

    def print_tree(hwnd, indent=0, max_depth=3):
        """递归打印窗口树"""
        if indent > max_depth or not hwnd:
            return
        cls = get_class(hwnd)
        title = get_title(hwnd)
        vis = user32.IsWindowVisible(hwnd)
        prefix = "  " * indent
        info = f"hwnd={hwnd} class={cls}"
        if title:
            info += f' title="{title}"'
        if not vis:
            info += " [隐藏]"
        print(f"{prefix}{info}")
        for child in enum_children(hwnd):
            print_tree(child, indent + 1, max_depth)

    # 1. 检查 DWM 组合
    try:
        dwmapi = ctypes.windll.dwmapi
        enabled = ctypes.c_int(0)
        dwmapi.DwmIsCompositionEnabled(ctypes.byref(enabled))
        print(f"\n[1] DWM 组合: {'已启用' if enabled.value else '未启用'}")
    except Exception as e:
        print(f"\n[1] DWM 检查失败: {e}")

    # 2. Progman
    progman = user32.FindWindowW("Progman", None)
    print(f"\n[2] Progman hwnd: {progman}")
    if progman:
        print("  Progman 的子窗口:")
        for child in enum_children(progman):
            cls = get_class(child)
            print(f"    hwnd={child} class={cls}")

    # 3. 发送 0x052C
    print(f"\n[3] 发送 0x052C 到 Progman...")
    result = ctypes.c_ulong(0)
    ret = user32.SendMessageTimeoutW(
        progman, 0x052C, 0, 0,
        0x0002, 5000, ctypes.byref(result)
    )
    print(f"    返回: ret={ret}, result={result.value}")

    # 4. 再次检查 Progman 子窗口
    print(f"\n[4] 发送消息后 Progman 的子窗口:")
    for child in enum_children(progman):
        cls = get_class(child)
        print(f"    hwnd={child} class={cls}")

    # 5. 枚举所有顶层 WorkerW
    print(f"\n[5] 枚举所有顶层窗口中的 WorkerW:")
    workerw_count = 0
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )

    def _enum_top(hwnd, _):
        nonlocal workerw_count
        cls = get_class(hwnd)
        if cls == "WorkerW":
            workerw_count += 1
            shell = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
            children = enum_children(hwnd)
            child_classes = [get_class(c) for c in children[:5]]
            print(f"    WorkerW #{workerw_count}: hwnd={hwnd}")
            print(f"      SHELLDLL_DefView: {bool(shell)} (hwnd={shell})")
            print(f"      子窗口: {child_classes}")
        return True

    user32.EnumWindows(EnumWindowsProc(_enum_top), 0)
    if workerw_count == 0:
        print("    (没有找到任何 WorkerW)")

    # 6. 直接找 SHELLDLL_DefView
    print(f"\n[6] 直接查找 SHELLDLL_DefView:")
    shell_hwnd = user32.FindWindowW("SHELLDLL_DefView", None)
    if shell_hwnd:
        parent = user32.GetParent(shell_hwnd)
        print(f"    找到: hwnd={shell_hwnd}, 父窗口={parent} (class={get_class(parent)})")
    else:
        print("    未找到 SHELLDLL_DefView")

    # 7. 桌面窗口
    desktop = user32.GetDesktopWindow()
    print(f"\n[7] 桌面窗口 hwnd: {desktop}")
    print("    桌面子窗口:")
    for child in enum_children(desktop):
        cls = get_class(child)
        print(f"      hwnd={child} class={cls}")

    print("\n" + "=" * 60)
    print("  诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    debug_workerw()
