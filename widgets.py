"""Widget classes for Desktop Organizer: sphere buttons, radial menu, circle area."""

import math
import random
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMenu, QInputDialog, QColorDialog, QMessageBox,
    QLineEdit, QDialog, QDialogButtonBox, QFileDialog, QApplication
)
from PyQt5.QtCore import Qt, QPoint, QSize, pyqtSignal, QRectF, QTimer, QThread, QEvent
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QCursor, QPainterPath, QBrush, QPen,
    QPixmap, QImage, QImageReader, QRadialGradient, QLinearGradient, QIcon
)

from constants import SPHERE_SKINS, MENU_STYLE, _BASE_DIR
from icon_utils import get_icon_pixmap, _resolve_path, _to_storage_path, _move_to_collect


class AppButton(QPushButton):
    """Small 3D sphere button showing an app icon, used inside RadialMenu."""
    rightClicked = pyqtSignal()

    def __init__(self, name, color, icon_path="", parent=None):
        super().__init__(parent)
        self.app_name = name
        self.base_color = QColor(color)
        self.setFixedSize(120, 120)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._anim_opacity = 1.0
        self._anim_scale = 1.0
        self._icon_pixmap = get_icon_pixmap(icon_path, 48) if icon_path else None
        if not self._icon_pixmap:
            label = name[:2] if len(name) >= 2 else name
            self.setText(label)
        self._cached_sphere = None
        self._cached_hover = None

    def _get_skin(self):
        skin_key = getattr(CategoryCircleButton, 'current_skin', 'default') or 'default'
        if skin_key.startswith("custom:") and hasattr(CategoryCircleButton, '_custom_skin_data'):
            return CategoryCircleButton._custom_skin_data or SPHERE_SKINS["default"]
        return SPHERE_SKINS.get(skin_key, SPHERE_SKINS["default"])

    def _render_cache(self):
        """Render sphere with liquid glass effect."""
        w, h = self.width(), self.height()
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing, True)
        c = self.base_color
        r = min(w, h) / 2.0
        cx, cy = w / 2, h / 2

        # Main sphere body with gradient
        hh, ss, vv, _ = c.getHsv()
        grad = QRadialGradient(cx * 0.85, cy * 0.7, r * 0.2, cx, cy, r)
        grad.setColorAt(0.0, QColor.fromHsv(hh, min(255, ss + 30), min(255, vv + 80), 255))
        grad.setColorAt(0.3, c)
        grad.setColorAt(0.7, QColor.fromHsv(hh, ss, max(0, int(vv * 0.5)), 240))
        grad.setColorAt(1.0, QColor.fromHsv(hh, ss, max(0, int(vv * 0.2)), 220))

        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawEllipse(2, 2, w - 4, h - 4)

        # Top highlight (liquid glass)
        highlight = QRadialGradient(cx * 0.7, cy * 0.4, r * 0.4, cx * 0.7, cy * 0.4)
        highlight.setColorAt(0, QColor(255, 255, 255, 60))
        highlight.setColorAt(0.5, QColor(255, 255, 255, 20))
        highlight.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(highlight)
        p.drawEllipse(int(cx - r * 0.6), int(cy - r * 0.7), int(r * 1.2), int(r * 0.8))

        # Bottom reflection
        bottom = QRadialGradient(cx, cy + r * 0.3, r * 0.5, cx, cy + r * 0.3)
        bottom.setColorAt(0, QColor(255, 255, 255, 15))
        bottom.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(bottom)
        p.drawEllipse(int(cx - r * 0.4), int(cy + r * 0.2), int(r * 0.8), int(r * 0.5))

        # Subtle border
        p.setPen(QPen(QColor(255, 255, 255, 50), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(3, 3, w - 6, h - 6)

        # Icon or text
        if self._icon_pixmap:
            p.save()
            clip = QPainterPath()
            clip.addEllipse(4, 4, w - 8, h - 8)
            p.setClipPath(clip)
            icon_size = min(48, int(r * 0.7))
            scaled = self._icon_pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ix = (w - scaled.width()) // 2
            iy = (h - scaled.height()) // 2 - 8
            p.drawPixmap(ix, iy, scaled)
            p.restore()
            # App name below icon
            p.setPen(QColor(255, 255, 255, 210))
            p.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
            p.drawText(QRectF(0, h * 0.62, w, h * 0.3), Qt.AlignHCenter | Qt.AlignTop, self.app_name)
        else:
            # Text only
            p.setPen(QColor(255, 255, 255, 230))
            p.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self.app_name)

        p.end()
        self._cached_sphere = pixmap

        # Hover glow overlay
        glow = QPixmap(w, h)
        glow.fill(Qt.transparent)
        gp = QPainter(glow)
        gp.setRenderHint(QPainter.Antialiasing, True)
        g = QRadialGradient(cx, cy, r + 6, cx, cy, r)
        g.setColorAt(0.8, QColor(255, 255, 255, 0))
        g.setColorAt(0.92, QColor(255, 255, 255, 35))
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        gp.setBrush(g)
        gp.setPen(Qt.NoPen)
        gp.drawEllipse(-4, -4, w + 8, h + 8)
        gp.setPen(QPen(QColor(255, 255, 255, 40), 1.5))
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
        # Pixmap cache — parent CircleArea.paintEvent draws this
        self._cached_pixmap = None
        self._cached_hover_state = False
        self._cached_skin_key = None
        self._cached_color = None
        # Ripple effect
        self._ripple_phase = 0.0
        self._ripple_active = False
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
        # Also check if pulse has changed enough to invalidate
        pulse_valid = True
        parent = self.parent()
        if parent and hasattr(parent, '_pulse_phase'):
            pulse_valid = abs(parent._pulse_phase - getattr(self, '_last_pulse', 0)) < 0.15
        return (self._cached_pixmap is not None
                and self._cached_hover_state == self._hover
                and self._cached_skin_key == skin_key
                and self._cached_color == color_val
                and pulse_valid)

    def _render_to_cache(self, size=160, pulse=0.0):
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
            
            # Ripple effect
            if self._ripple_active:
                ripple_r = r + 20 * self._ripple_phase
                ripple_alpha = int(60 * (1 - self._ripple_phase))
                if ripple_alpha > 0:
                    ripple_pen = QPen(QColor(glow_color.red(), glow_color.green(),
                                            glow_color.blue(), ripple_alpha), 2)
                    painter.setPen(ripple_pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(int(cx - ripple_r), int(cy - ripple_r),
                                       int(ripple_r * 2), int(ripple_r * 2))
        
        # ── Breathing glow (subtle pulse) ──
        if not self._hover:
            # Get pulse from parent
            pulse = 0.0
            parent = self.parent()
            if parent and hasattr(parent, '_pulse_phase'):
                pulse = parent._pulse_phase
            breath_alpha = int(15 + 10 * math.sin(pulse + hash(str(id(self))) * 0.1))
            breath_color = QColor(c.red(), c.green(), c.blue(), breath_alpha)
            painter.setPen(Qt.NoPen)
            painter.setBrush(breath_color)
            painter.drawEllipse(-2, -2, w + 4, h + 4)

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
        """Transparent — spheres are drawn in parent CircleArea.paintEvent."""
        pass

    def _ensure_cache(self):
        """Make sure the cached pixmap is rendered."""
        if not self._is_cache_valid():
            # Get pulse from parent CircleArea if available
            pulse = 0.0
            parent = self.parent()
            if parent and hasattr(parent, '_pulse_phase'):
                pulse = parent._pulse_phase
            self._render_to_cache(pulse=pulse)
            self._last_pulse = pulse

    def enterEvent(self, e):
        self._hover = True
        self._ripple_active = True
        self._ripple_phase = 0.0
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

    def update_ripple(self):
        """Update ripple animation. Called by parent CircleArea."""
        if self._ripple_active:
            self._ripple_phase += 0.05
            if self._ripple_phase >= 1.0:
                self._ripple_active = False
                self._ripple_phase = 0.0
            self._cached_pixmap = None
            self._ensure_cache()

    def contextMenuEvent(self, e):
        self.menuRequested.emit(self)
        e.accept()


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
        cx, cy = w // 2, h // 2

        if not items:
            return

        angle_step = 360.0 / len(items)
        start_angle = -90
        btn_size = 120  # Match AppButton size

        for i, item in enumerate(items):
            angle = math.radians(start_angle + i * angle_step)
            tx = int(cx + radius * math.cos(angle) - btn_size // 2)
            ty = int(cy + radius * math.sin(angle) - btn_size // 2)
            self._target_positions.append((tx, ty))

            btn = AppButton(item["name"], color, "", self)
            btn.move(int(cx) - btn_size // 2, int(cy) - btn_size // 2)
            btn.clicked.connect(lambda checked, it=item: self._open_item(it))
            btn.rightClicked.connect(lambda it=item: self._show_item_menu(it))
            btn.hide()
            self._app_buttons.append(btn)

        # Load icons in background (Python thread, not QThread)
        QTimer.singleShot(0, lambda: self._load_icons_threaded(items))

    def _load_icons_threaded(self, items):
        """Load icons in a daemon Python thread."""
        import threading
        def _worker():
            results = []
            for item in items:
                path = item.get("path", "")
                if not path:
                    results.append(None)
                    continue
                results.append(get_icon_pixmap(path, 48))
            # Apply on main thread
            QTimer.singleShot(0, lambda: self._apply_icons(results, len(results)))
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

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
            btn_size = 120
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
                    cur_x = cx - btn_size // 2 + (tx - (cx - btn_size // 2)) * pos_ease
                    cur_y = cy - btn_size // 2 + (ty - (cy - btn_size // 2)) * pos_ease
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
            btn_size = 120
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
        cx, cy = w // 2, h // 2
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

class CircleArea(QWidget):
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
        
        # Star particles
        self._particles = []
        self._particle_colors = [
            QColor(255, 255, 255),  # white
            QColor(255, 220, 180),  # warm white
            QColor(180, 200, 255),  # blue tint
            QColor(255, 200, 220),  # pink tint
            QColor(200, 255, 220),  # green tint
        ]
        
        # Pulse animation for spheres
        self._pulse_phase = 0.0

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
        self._render_timer.start(33)  # 30fps active
        self._is_idle = False
        self._dirty = True  # need repaint

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
        active = self._flying_in or self._mouse_active or self._move_mode or self._dragging
        
        # Dynamic frame rate: always 30fps
        if active and self._is_idle:
            self._is_idle = False
            self._render_timer.setInterval(33)
            self._dirty = True
        elif not active and not self._is_idle:
            self._is_idle = True
            self._render_timer.setInterval(33)
        
        self._phase += 0.04
        self._dirty = True

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

        # Slow auto-rotate (always)
        self._angle += 0.015
        self._pulse_phase += 0.03  # Pulse animation
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
            # Update ripple animation
            if btn._ripple_active:
                btn.update_ripple()
                any_dirty = True

        self._update_positions(self._btn_entries)
        # Update particles
        self._update_particles()
        # Only repaint if something changed
        if any_dirty or self._dirty or not self._is_idle or self._particles:
            self._dirty = False
            self.update()

    def _spawn_particles(self, x, y, count=3):
        """Spawn star particles at position."""
        import random
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2.5)
            size = random.uniform(1.5, 4.0)
            lifetime = random.uniform(20, 50)
            color = random.choice(self._particle_colors)
            self._particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - 1,  # slight upward bias
                'size': size,
                'life': lifetime,
                'max_life': lifetime,
                'color': color,
            })

    def _update_particles(self):
        """Update particle positions and remove dead ones."""
        alive = []
        for p in self._particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.02  # gravity
            p['life'] -= 1
            if p['life'] > 0:
                alive.append(p)
        self._particles = alive

    def _draw_particles(self, painter):
        """Draw all active particles."""
        for p in self._particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            size = p['size'] * (p['life'] / p['max_life'])
            color = QColor(p['color'])
            color.setAlpha(alpha)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(int(p['x'] - size/2), int(p['y'] - size/2), int(size), int(size))
            # Glow
            glow = QColor(p['color'])
            glow.setAlpha(alpha // 3)
            painter.setBrush(glow)
            painter.drawEllipse(int(p['x'] - size), int(p['y'] - size), int(size * 2), int(size * 2))

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
        # Spawn particles at mouse position
        self._spawn_particles(e.x(), e.y(), 2)

    def leaveEvent(self, e):
        self._mouse_active = False
        self._set_hover(None)

    def resizeEvent(self, e):
        """窗口大小变化时重算球环位置"""
        super().resizeEvent(e)
        if hasattr(self, '_btn_entries') and self._btn_entries:
            self._update_positions(self._btn_entries)

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self._dragging = False

    # ── Paint (background decorations) ─────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # 壁纸模式：跳过背景和装饰，只画球体
        if not getattr(self, '_wallpaper_mode', False):
            # Custom background image or color (wallpaper engine)
            bg_color = self._get_data("bg_color")
            wp_type = self._wallpaper_manager.get_type() if self._wallpaper_manager else None
            # [DEBUG] 写文件排查走了哪个分支
            if not hasattr(self, '_debug_logged'):
                self._debug_logged = True
                try:
                    with open("debug_paint.txt", "w", encoding="utf-8") as _f:
                        _f.write(f"wp_type={wp_type}\n")
                        _f.write(f"bg_color={bg_color!r}\n")
                        _f.write(f"bg_pixmap={self._bg_pixmap}\n")
                        _f.write(f"wp_mgr={self._wallpaper_manager}\n")
                        _f.write(f"wp_mode={getattr(self, '_wallpaper_mode', False)}\n")
                except Exception:
                    pass
            if self._wallpaper_manager and wp_type in ("image", "video"):
                self._wallpaper_manager.paint(painter, self.rect())
                painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 100))
            elif self._bg_pixmap and not self._bg_pixmap.isNull():
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
            else:
                # [DEBUG] 银河星空背景
                import logging as _dbg_log
                _dbg_log.getLogger("debug").warning(
                    f"PAINT_GALAXY: wp_type={wp_type}, bg_color={bg_color!r}, "
                    f"bg_pixmap={self._bg_pixmap}, wp_mgr={self._wallpaper_manager}"
                )
                # 深空底色
                painter.fillRect(0, 0, w, h, QColor(5, 5, 18))

                # 星云层1：紫色星云（左上）
                if not hasattr(self, '_cached_nebula1') or self._cached_nebula1_size != (w, h):
                    n1 = QRadialGradient(w * 0.2, h * 0.25, min(w, h) * 0.35, w * 0.2, h * 0.25)
                    n1.setColorAt(0, QColor(80, 30, 120, 45))
                    n1.setColorAt(0.3, QColor(60, 20, 100, 30))
                    n1.setColorAt(0.7, QColor(30, 10, 60, 15))
                    n1.setColorAt(1, QColor(0, 0, 0, 0))
                    self._cached_nebula1 = QBrush(n1)
                    self._cached_nebula1_size = (w, h)
                painter.fillRect(0, 0, w, h, self._cached_nebula1)

                # 星云层2：蓝色星云（右下）
                if not hasattr(self, '_cached_nebula2') or self._cached_nebula2_size != (w, h):
                    n2 = QRadialGradient(w * 0.75, h * 0.7, min(w, h) * 0.4, w * 0.75, h * 0.7)
                    n2.setColorAt(0, QColor(20, 50, 120, 40))
                    n2.setColorAt(0.3, QColor(15, 35, 90, 25))
                    n2.setColorAt(0.7, QColor(8, 18, 50, 10))
                    n2.setColorAt(1, QColor(0, 0, 0, 0))
                    self._cached_nebula2 = QBrush(n2)
                    self._cached_nebula2_size = (w, h)
                painter.fillRect(0, 0, w, h, self._cached_nebula2)

                # 星云层3：粉色星云（中心偏右）
                if not hasattr(self, '_cached_nebula3') or self._cached_nebula3_size != (w, h):
                    n3 = QRadialGradient(w * 0.55, h * 0.45, min(w, h) * 0.25, w * 0.55, h * 0.45)
                    n3.setColorAt(0, QColor(100, 25, 60, 30))
                    n3.setColorAt(0.5, QColor(60, 15, 40, 15))
                    n3.setColorAt(1, QColor(0, 0, 0, 0))
                    self._cached_nebula3 = QBrush(n3)
                    self._cached_nebula3_size = (w, h)
                painter.fillRect(0, 0, w, h, self._cached_nebula3)

                # 银河带（对角线亮带）
                if not hasattr(self, '_cached_milkyway') or self._cached_milkyway_size != (w, h):
                    from PyQt5.QtGui import QPolygonF
                    from PyQt5.QtCore import QPointF
                    # 创建一条从左下到右上的半透明亮带
                    mw = QLinearGradient(w * 0.1, h * 0.9, w * 0.9, h * 0.1)
                    mw.setColorAt(0, QColor(0, 0, 0, 0))
                    mw.setColorAt(0.2, QColor(100, 80, 60, 12))
                    mw.setColorAt(0.4, QColor(140, 120, 100, 18))
                    mw.setColorAt(0.5, QColor(160, 140, 120, 22))
                    mw.setColorAt(0.6, QColor(140, 120, 100, 18))
                    mw.setColorAt(0.8, QColor(100, 80, 60, 12))
                    mw.setColorAt(1, QColor(0, 0, 0, 0))
                    self._cached_milkyway = QBrush(mw)
                    self._cached_milkyway_size = (w, h)
                painter.fillRect(0, 0, w, h, self._cached_milkyway)

                # 静态星星（缓存）
                if not hasattr(self, '_cached_stars') or self._cached_stars_size != (w, h):
                    import random
                    random.seed(42)  # 固定种子，每次相同
                    star_pixmap = QPixmap(w, h)
                    star_pixmap.fill(Qt.transparent)
                    sp = QPainter(star_pixmap)
                    sp.setRenderHint(QPainter.Antialiasing)
                    for _ in range(200):
                        sx = random.randint(0, w)
                        sy = random.randint(0, h)
                        brightness = random.randint(80, 255)
                        size = random.choice([1, 1, 1, 1, 2, 2, 3])
                        alpha = int(brightness * 0.7)
                        sp.setPen(Qt.NoPen)
                        sp.setBrush(QColor(255, 255, 255, alpha))
                        sp.drawEllipse(sx, sy, size, size)
                    sp.end()
                    self._cached_stars = star_pixmap
                    self._cached_stars_size = (w, h)
                painter.drawPixmap(0, 0, self._cached_stars)

                # 动态闪烁星星
                painter.setPen(Qt.NoPen)
                for i in range(30):
                    fx = int((hash(f"star_x_{i}") % 10000) / 10000 * w)
                    fy = int((hash(f"star_y_{i}") % 10000) / 10000 * h)
                    flicker = int(60 + 80 * abs(math.sin(self._phase * 0.8 + i * 1.3)))
                    painter.setBrush(QColor(255, 255, 255, flicker))
                    painter.drawEllipse(fx - 1, fy - 1, 3, 3)

            # Vignette
            if self._cached_vignette_size != (w, h):
                vignette = QRadialGradient(cx, cy, max(w, h) * 0.55, cx, cy)
                vignette.setColorAt(0.5, QColor(0, 0, 0, 0))
                vignette.setColorAt(0.85, QColor(0, 0, 0, 12))
                vignette.setColorAt(1.0, QColor(0, 0, 0, 30))
                self._cached_vignette = QBrush(vignette)
                self._cached_vignette_size = (w, h)
            painter.fillRect(0, 0, w, h, self._cached_vignette)

            # ── 多层暖金装饰背景 ──
            r = min(cx, cy) - 30

            # 层0: 大范围暖色光晕（底层氛围）
            painter.setPen(Qt.NoPen)
            ambient = QRadialGradient(cx, cy, r * 1.2, cx, cy)
            ambient.setColorAt(0, QColor(255, 255, 255, 15))
            ambient.setColorAt(0.4, QColor(255, 255, 255, 6))
            ambient.setColorAt(0.8, QColor(255, 255, 255, 2))
            ambient.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(ambient)
            painter.drawEllipse(int(cx - r * 1.2), int(cy - r * 1.2),
                               int(r * 2.4), int(r * 2.4))

            # 层1: 径向网格线（12条，更密）
            painter.save()
            for i in range(12):
                angle = i * math.pi / 6
                x1 = cx + int(r * 0.12 * math.cos(angle))
                y1 = cy + int(r * 0.12 * math.sin(angle))
                x2 = cx + int(r * math.cos(angle))
                y2 = cy + int(r * math.sin(angle))
                alpha = int(18 + 8 * math.sin(self._phase * 0.5 + i))
                painter.setPen(QPen(QColor(255, 255, 255, alpha), 0.6))
                painter.drawLine(x1, y1, x2, y2)
            painter.restore()

            # 层2: 多层同心环（外→内，暖金脉动）
            rings = [
                (r, 1.2, 30, 1.0),
                (r * 0.85, 1.0, 45, 1.2),
                (r * 0.65, 0.8, 35, 1.0),
                (r * 0.45, 0.6, 25, 0.8),
                (r * 0.25, 0.4, 18, 0.6),
            ]
            for ring_r, pulse_speed, base_alpha, line_w in rings:
                glow = int(base_alpha + 12 * math.sin(self._phase * pulse_speed))
                painter.setPen(QPen(QColor(255, 255, 255, glow), line_w))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(int(cx - ring_r), int(cy - ring_r),
                                   int(ring_r * 2), int(ring_r * 2))

            # 层3: 中心暖金光晕（更强）
            center_glow = QRadialGradient(cx, cy, r * 0.45, cx, cy)
            pulse_intensity = 0.15 + 0.08 * math.sin(self._phase * 0.8)
            center_glow.setColorAt(0, QColor(255, 255, 255, int(255 * pulse_intensity)))
            center_glow.setColorAt(0.3, QColor(255, 255, 255, int(255 * pulse_intensity * 0.5)))
            center_glow.setColorAt(0.7, QColor(255, 255, 255, int(255 * pulse_intensity * 0.1)))
            center_glow.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(center_glow)
            painter.drawEllipse(int(cx - r * 0.45), int(cy - r * 0.45),
                               int(r * 0.9), int(r * 0.9))

            # 层4: 装饰性小圆点（两圈，内外）
            painter.setPen(Qt.NoPen)
            # 外圈
            for i in range(16):
                dot_angle = self._phase * 0.25 + i * math.pi / 8
                dot_r = r - 5
                dx = cx + int(dot_r * math.cos(dot_angle))
                dy = cy + int(dot_r * math.sin(dot_angle))
                dot_alpha = int(50 + 30 * math.sin(self._phase + i * 0.7))
                painter.setBrush(QColor(255, 255, 255, dot_alpha))
                painter.drawEllipse(dx - 2, dy - 2, 4, 4)
            # 内圈
            for i in range(8):
                dot_angle = -self._phase * 0.4 + i * math.pi / 4
                dot_r = r * 0.35
                dx = cx + int(dot_r * math.cos(dot_angle))
                dy = cy + int(dot_r * math.sin(dot_angle))
                dot_alpha = int(35 + 20 * math.sin(self._phase * 1.2 + i))
                painter.setBrush(QColor(255, 255, 255, dot_alpha))
                painter.drawEllipse(dx - 1, dy - 1, 3, 3)

            # 层5: 中心文字（暖金色）- 已移除

        # ── Draw category spheres (rendered in parent, not by child widgets) ──
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        for btn, sx, sy, sz, opacity, _ in self._projected:
            pixmap = getattr(btn, '_cached_pixmap', None)
            if pixmap and not pixmap.isNull():
                painter.setOpacity(opacity)
                half = sz // 2
                painter.drawPixmap(int(sx - half), int(sy - half), sz, sz, pixmap)
        painter.setOpacity(1.0)

        # Category name labels under each sphere
        painter.setPen(QColor(255, 248, 235, 180))
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        for btn, sx, sy, sz, opacity, _ in self._projected:
            if opacity < 0.3:
                continue
            cat = btn.category_data
            name = cat.get("name", "")
            count = len(cat.get("items", []))
            label = f"{name}"
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            lx = int(sx - tw / 2)
            ly = int(sy + sz // 2 + 10)
            painter.setOpacity(opacity * 0.85)
            painter.drawText(lx, ly, tw, fm.height(), Qt.AlignCenter, label)
            # Count below name
            if count > 0:
                painter.setPen(QColor(255, 255, 255, int(120 * opacity)))
                painter.setFont(QFont("Microsoft YaHei", 7))
                count_text = f"{count} 个应用"
                ctw = fm.horizontalAdvance(count_text)
                painter.drawText(int(sx - ctw / 2), ly + fm.height() + 2, ctw, fm.height(),
                                 Qt.AlignCenter, count_text)
                painter.setPen(QColor(255, 248, 235, 180))
                painter.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        painter.setOpacity(1.0)

        # Hover tooltip — category name + item count
        if self._hovered_btn:
            cat = self._hovered_btn.category_data
            name = cat.get("name", "")
            count = len(cat.get("items", []))
            for btn, sx, sy, sz, _, _ in self._projected:
                if btn is self._hovered_btn:
                    text = f"{name} ({count}项)" if count else name
                    font = QFont("Microsoft YaHei", 10, QFont.Bold)
                    painter.setFont(font)
                    fm = painter.fontMetrics()
                    tw = fm.horizontalAdvance(text) + 16
                    th = fm.height() + 8
                    tx = int(sx - tw / 2)
                    ty = int(sy + sz / 2 + 28)
                    # Warm glass pill background
                    painter.setOpacity(0.9)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(42, 31, 20, 220))
                    painter.drawRoundedRect(tx - 2, ty - 2, tw + 4, th + 4, 8, 8)
                    painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(tx - 2, ty - 2, tw + 4, th + 4, 8, 8)
                    painter.setOpacity(1.0)
                    painter.setPen(QColor(255, 248, 235))
                    painter.drawText(tx, ty, tw, th, Qt.AlignCenter, text)
                    break

        # Draw particles
        self._draw_particles(painter)

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


class SystemMonitorWidget(QWidget):
    """Floating system monitor panel showing CPU, memory, and network speed."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(280, 220)
        
        # Data
        self._cpu_percent = 0.0
        self._mem_percent = 0.0
        self._mem_used = 0.0
        self._mem_total = 0.0
        self._net_sent_speed = 0.0
        self._net_recv_speed = 0.0
        self._last_net_sent = 0.0
        self._last_net_recv = 0.0
        self._last_time = 0.0
        
        # Timer for updates
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(1000)
        self._update_stats()
        
    def _update_stats(self):
        import psutil
        import time
        
        # CPU
        self._cpu_percent = psutil.cpu_percent(interval=0)
        
        # Memory
        mem = psutil.virtual_memory()
        self._mem_percent = mem.percent
        self._mem_used = mem.used / (1024 ** 3)
        self._mem_total = mem.total / (1024 ** 3)
        
        # Network
        net = psutil.net_io_counters()
        current_time = time.time()
        dt = current_time - self._last_time
        
        if dt > 0 and self._last_time > 0:
            self._net_sent_speed = (net.bytes_sent - self._last_net_sent) / dt
            self._net_recv_speed = (net.bytes_recv - self._last_net_recv) / dt
        
        self._last_net_sent = net.bytes_sent
        self._last_net_recv = net.bytes_recv
        self._last_time = current_time
        
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        w, h = self.width(), self.height()
        
        # Frosted glass background
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.setBrush(QColor(20, 20, 35, 180))
        painter.drawRoundedRect(0, 0, w, h, 12, 12)
        
        # Title - use rect form
        painter.setPen(QColor(255, 255, 255, 180))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        painter.drawText(QRectF(10, 8, 200, 25), Qt.AlignVCenter, "系统监控")
        
        # Separator line
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawLine(10, 35, w - 10, 35)
        
        # ── CPU Section ──
        bar_x, bar_w, bar_h = 55, 180, 14
        
        # Label - use rect form
        painter.setPen(QColor(255, 255, 255, 120))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(QRectF(15, 42, 35, 20), Qt.AlignVCenter, "CPU")
        
        # Progress bar background
        bar_y = 45
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 20))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 7, 7)
        # Fill
        fill_w = int(bar_w * self._cpu_percent / 100)
        if fill_w > 0:
            if self._cpu_percent < 50:
                color = QColor(100, 200, 150, 200)
            elif self._cpu_percent < 80:
                color = QColor(200, 180, 100, 200)
            else:
                color = QColor(200, 100, 100, 200)
            painter.setBrush(color)
            painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 7, 7)
        # Value - use rect form
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(bar_x + bar_w + 8, bar_y, 40, bar_h), Qt.AlignVCenter, f"{int(self._cpu_percent)}%")
        
        # ── Memory Section ──
        bar_y2 = 75
        
        # Label
        painter.setPen(QColor(255, 255, 255, 120))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(QRectF(15, 72, 35, 20), Qt.AlignVCenter, "内存")
        
        # Progress bar background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 20))
        painter.drawRoundedRect(bar_x, bar_y2, bar_w, bar_h, 7, 7)
        # Fill
        fill_w2 = int(bar_w * self._mem_percent / 100)
        if fill_w2 > 0:
            painter.setBrush(QColor(100, 150, 220, 200))
            painter.drawRoundedRect(bar_x, bar_y2, fill_w2, bar_h, 7, 7)
        # Value
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(bar_x + bar_w + 8, bar_y2, 40, bar_h), Qt.AlignVCenter, f"{int(self._mem_percent)}%")
        
        # Memory detail - use rect form
        painter.setPen(QColor(255, 255, 255, 140))
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.drawText(QRectF(55, bar_y2 + bar_h + 2, 180, 16), Qt.AlignVCenter, f"{self._mem_used:.1f} / {self._mem_total:.1f} GB")
        
        # ── Network Section ──
        # Label
        painter.setPen(QColor(255, 255, 255, 120))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(QRectF(15, 122, 35, 20), Qt.AlignVCenter, "网络")
        
        def fmt(bps):
            if bps < 1024:
                return f"{bps:.0f} B/s"
            elif bps < 1024*1024:
                return f"{bps/1024:.1f} KB/s"
            else:
                return f"{bps/(1024*1024):.1f} MB/s"
        
        # Upload - use rect form
        painter.setPen(QColor(150, 255, 150, 180))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(55, 138, 180, 16), Qt.AlignVCenter, f"↑ {fmt(self._net_sent_speed)}")
        
        # Download - use rect form
        painter.setPen(QColor(150, 200, 255, 180))
        painter.drawText(QRectF(55, 158, 180, 16), Qt.AlignVCenter, f"↓ {fmt(self._net_recv_speed)}")
        
        painter.end()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.pos()
            event.accept()
            
    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        if hasattr(self, '_drag_pos'):
            del self._drag_pos


class PomodoroTimer(QWidget):
    """Horizontal liquid glass Pomodoro timer."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Calculate size based on screen
        screen = QApplication.primaryScreen().geometry()
        w = int(screen.width() * 0.55)  # 55% of screen width
        h = int(w * 0.087)  # Maintain aspect ratio
        self.setFixedSize(w, h)
        
        # Timer state
        self._work_duration = 25 * 60
        self._break_duration = 5 * 60
        self._time_remaining = self._work_duration
        self._is_running = False
        self._is_work = True
        self._sessions_completed = 0
        self._session_number = 1
        
        # Timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        
        # Button hover
        self._hover_btn = None
        
    def _tick(self):
        if self._time_remaining > 0:
            self._time_remaining -= 1
        else:
            self._timer.stop()
            self._is_running = False
            if self._is_work:
                self._sessions_completed += 1
                self._session_number += 1
                self._is_work = False
                self._time_remaining = self._break_duration
            else:
                self._is_work = True
                self._time_remaining = self._work_duration
        self.update()
        
    def _toggle_start(self):
        if self._is_running:
            self._timer.stop()
            self._is_running = False
        else:
            self._timer.start(1000)
            self._is_running = True
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        w, h = self.width(), self.height()
        
        # ── Liquid glass background ──
        # Base dark layer
        base = QLinearGradient(0, 0, 0, h)
        base.setColorAt(0, QColor(50, 50, 60, 180))
        base.setColorAt(1, QColor(30, 30, 40, 200))
        painter.setPen(Qt.NoPen)
        painter.setBrush(base)
        painter.drawRoundedRect(0, 0, w, h, 20, 20)
        
        # Glass highlight (top)
        highlight = QLinearGradient(0, 0, 0, h * 0.4)
        highlight.setColorAt(0, QColor(255, 255, 255, 30))
        highlight.setColorAt(1, QColor(255, 255, 255, 5))
        painter.setBrush(highlight)
        painter.drawRoundedRect(0, 0, w, int(h * 0.4), 20, 20)
        
        # Glass spot (top-left glow)
        painter.setPen(Qt.NoPen)
        spot = QRadialGradient(90, 10, 60, 90, 10)
        spot.setColorAt(0, QColor(255, 255, 255, 35))
        spot.setColorAt(0.5, QColor(255, 255, 255, 10))
        spot.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(spot)
        painter.drawEllipse(30, -20, 120, 60)
        
        # Bottom reflection line
        painter.setPen(QPen(QColor(255, 255, 255, 75), 1))
        painter.drawLine(0, h - 1, w, h - 1)
        
        # Border
        border = QLinearGradient(0, 0, 0, h)
        border.setColorAt(0, QColor(255, 255, 255, 65))
        border.setColorAt(0.5, QColor(255, 255, 255, 45))
        border.setColorAt(1, QColor(255, 255, 255, 20))
        painter.setPen(QPen(QBrush(border), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(0, 0, w, h, 20, 20)
        
        # ── Left section: Session + Time ──
        painter.setPen(QColor(255, 255, 255, 115))
        painter.setFont(QFont("Segoe UI", int(w * 0.008)))
        painter.drawText(QRectF(w * 0.03, h * 0.15, w * 0.15, h * 0.2), Qt.AlignLeft, f"POMODORO #{self._session_number}")
        
        minutes = self._time_remaining // 60
        seconds = self._time_remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        
        painter.setPen(QColor(255, 255, 255, 245))
        painter.setFont(QFont("Segoe UI", int(w * 0.03), QFont.Bold))
        painter.drawText(QRectF(w * 0.03, h * 0.25, w * 0.22, h * 0.7), Qt.AlignLeft | Qt.AlignVCenter, time_str)
        
        # ── Divider line ──
        div_grad = QLinearGradient(0, h * 0.2, 0, h * 0.8)
        div_grad.setColorAt(0, QColor(255, 255, 255, 0))
        div_grad.setColorAt(0.5, QColor(255, 255, 255, 50))
        div_grad.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setPen(QPen(QBrush(div_grad), 1))
        painter.drawLine(int(w * 0.28), int(h * 0.2), int(w * 0.28), int(h * 0.8))
        
        # ── Middle section: Status ──
        if self._is_running:
            dot_color = QColor(80, 200, 120, 220) if self._is_work else QColor(200, 160, 80, 220)
        else:
            dot_color = QColor(255, 255, 255, 80)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(dot_color)
        painter.drawEllipse(int(w * 0.31), int(h * 0.4), int(h * 0.1), int(h * 0.1))
        
        if self._is_running:
            status = "学习中" if self._is_work else "休息中"
        else:
            status = "暂停"
        
        painter.setPen(QColor(255, 255, 255, 190))
        painter.setFont(QFont("Microsoft YaHei", int(w * 0.009)))
        painter.drawText(QRectF(w * 0.34, h * 0.35, w * 0.1, h * 0.3), Qt.AlignLeft | Qt.AlignVCenter, status)
        
        # ── Divider line 2 ──
        painter.setPen(QPen(QBrush(div_grad), 1))
        painter.drawLine(int(w * 0.46), int(h * 0.2), int(w * 0.46), int(h * 0.8))
        
        # ── Right section: Sessions progress ──
        painter.setPen(QColor(255, 255, 255, 115))
        painter.setFont(QFont("Microsoft YaHei", int(w * 0.007)))
        painter.drawText(QRectF(w * 0.49, h * 0.2, w * 0.1, h * 0.2), Qt.AlignLeft, "今日完成")
        
        dot_y = int(h * 0.5)
        dot_size = int(h * 0.12)
        dot_spacing = int(w * 0.02)
        total_dots = 4
        start_x = int(w * 0.49)
        
        for i in range(total_dots):
            dx = start_x + i * dot_spacing
            if i < self._sessions_completed:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(80, 200, 120, 200))
                painter.drawEllipse(dx, dot_y, dot_size, dot_size)
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
                painter.setBrush(QColor(255, 255, 255, 20))
                painter.drawEllipse(dx, dot_y, dot_size, dot_size)
        
        # ── Action button: liquid glass ──
        btn_x = int(w * 0.82)
        btn_y = int(h * 0.25)
        btn_w = int(w * 0.12)
        btn_h = int(h * 0.5)
        
        # Button background
        if self._hover_btn == 'start':
            btn_bg = QColor(255, 255, 255, 65)
        else:
            btn_bg = QColor(255, 255, 255, 40)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(btn_bg)
        painter.drawRoundedRect(btn_x, btn_y, btn_w, btn_h, 16, 16)
        
        # Button highlight
        btn_highlight = QLinearGradient(btn_x, btn_y, btn_x, btn_y + btn_h * 0.5)
        btn_highlight.setColorAt(0, QColor(255, 255, 255, 40))
        btn_highlight.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(btn_highlight)
        painter.drawRoundedRect(btn_x, btn_y, btn_w, int(btn_h * 0.5), 16, 16)
        
        # Button border
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(btn_x, btn_y, btn_w, btn_h, 16, 16)
        
        # Button text
        btn_text = "暂停" if self._is_running else "专注模式"
        painter.setPen(QColor(255, 255, 255, 230))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        painter.drawText(QRectF(btn_x, btn_y, btn_w, btn_h), Qt.AlignCenter, btn_text)
        
        painter.end()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            w = self.width()
            h = self.height()
            btn_x = int(w * 0.82)
            btn_y = int(h * 0.25)
            btn_w = int(w * 0.12)
            btn_h = int(h * 0.5)
            
            if btn_x <= x <= btn_x + btn_w and btn_y <= y <= btn_y + btn_h:
                self._toggle_start()
                return
                
            self._drag_pos = event.globalPos() - self.pos()
            event.accept()
            
    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        else:
            x, y = event.x(), event.y()
            w = self.width()
            h = self.height()
            btn_x = int(w * 0.82)
            btn_y = int(h * 0.25)
            btn_w = int(w * 0.12)
            btn_h = int(h * 0.5)
            
            old_hover = self._hover_btn
            if btn_x <= x <= btn_x + btn_w and btn_y <= y <= btn_y + btn_h:
                self._hover_btn = 'start'
            else:
                self._hover_btn = None
                
            if old_hover != self._hover_btn:
                self.setCursor(Qt.PointingHandCursor if self._hover_btn else Qt.ArrowCursor)
                self.update()
            
    def mouseReleaseEvent(self, event):
        if hasattr(self, '_drag_pos'):
            del self._drag_pos
