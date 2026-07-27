"""Dialog classes for Desktop Organizer: settings, custom skin, app rules."""

import time
import json
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMenu, QInputDialog, QColorDialog, QMessageBox,
    QLineEdit, QDialog, QSlider, QComboBox,
    QDialogButtonBox, QScrollArea, QTabWidget, QRadioButton,
    QButtonGroup, QGroupBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QPoint, QSize, pyqtSignal, QRectF, QTimer
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QCursor, QPainterPath, QBrush, QPen,
    QPixmap, QImage, QImageReader, QRadialGradient, QLinearGradient, QIcon
)

from constants import APP_VERSION, SPHERE_SKINS, MENU_STYLE, _BASE_DIR, CHANGELOG_FILE, LIQUID_GLASS_DIALOG_STYLE
from widgets import SkinPreview


class CustomSkinDialog(QDialog):
    """Dialog for creating/editing a custom sphere skin."""

    def __init__(self, parent=None, existing=None, color="#4A90D9"):
        super().__init__(parent)
        self.setWindowTitle("自定义皮肤")
        self.setFixedSize(480, 620)
        self.setStyleSheet(LIQUID_GLASS_DIALOG_STYLE)

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


class _RuleCard(QFrame):
    """A single rule card widget with left color indicator and description."""
    clicked = pyqtSignal(int)

    CARD_STYLE = """
        QFrame {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
        }
        QFrame:hover {
            background: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.1);
        }
    """
    CARD_SELECTED_STYLE = """
        QFrame {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
        }
    """

    def __init__(self, index, exe_name, behavior, description="", parent=None):
        super().__init__(parent)
        self._index = index
        self._selected = False
        self._behavior = behavior
        self.setFixedHeight(70)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(self.CARD_STYLE)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 10, 16, 10)
        lay.setSpacing(14)

        # Left color indicator bar
        self._bar = QFrame()
        self._bar.setFixedSize(3, 36)
        bar_color = "rgba(255,166,77,0.6)" if behavior == "pause" else "rgba(102,187,106,0.6)"
        self._bar.setStyleSheet(f"background: {bar_color}; border-radius: 1px;")
        lay.addWidget(self._bar)

        # Icon
        self._icon_label = QLabel("⏸" if behavior == "pause" else "▶")
        self._icon_label.setFixedSize(40, 40)
        self._icon_label.setAlignment(Qt.AlignCenter)
        if behavior == "pause":
            self._icon_label.setStyleSheet(
                "background: rgba(255,166,77,0.08);"
                "border: 1px solid rgba(255,166,77,0.15);"
                "border-radius: 10px; font-size: 18px;"
            )
        else:
            self._icon_label.setStyleSheet(
                "background: rgba(102,187,106,0.08);"
                "border: 1px solid rgba(102,187,106,0.15);"
                "border-radius: 10px; font-size: 18px;"
            )
        lay.addWidget(self._icon_label)

        # Info
        info_lay = QVBoxLayout()
        info_lay.setSpacing(3)
        info_lay.setContentsMargins(0, 0, 0, 0)

        self._name_label = QLabel(exe_name)
        self._name_label.setStyleSheet(
            "color: rgba(255,255,255,0.85); font-size: 16px; font-weight: 500;"
            "font-family: 'Consolas', 'SF Mono', monospace;"
        )
        info_lay.addWidget(self._name_label)

        beh_text = "暂停" if behavior == "pause" else "保持运行"
        self._desc_label = QLabel(description if description else beh_text)
        self._desc_label.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 13px;")
        info_lay.addWidget(self._desc_label)

        lay.addLayout(info_lay, 1)

        # Behavior tag
        self._tag = QLabel(beh_text)
        if behavior == "pause":
            self._tag.setStyleSheet(
                "background: rgba(255,166,77,0.08);"
                "border: 1px solid rgba(255,166,77,0.15);"
                "color: rgba(255,166,77,0.9);"
                "border-radius: 8px; padding: 5px 14px; font-size: 13px; font-weight: 500;"
            )
        else:
            self._tag.setStyleSheet(
                "background: rgba(102,187,106,0.08);"
                "border: 1px solid rgba(102,187,106,0.15);"
                "color: rgba(102,187,106,0.9);"
                "border-radius: 8px; padding: 5px 14px; font-size: 13px; font-weight: 500;"
            )
        self._tag.setFixedHeight(28)
        lay.addWidget(self._tag)

    def set_selected(self, selected):
        self._selected = selected
        self.setStyleSheet(self.CARD_SELECTED_STYLE if selected else self.CARD_STYLE)
        bar_color = ("rgba(255,166,77,0.8)" if self._behavior == "pause"
                     else "rgba(102,187,106,0.8)")
        if not selected:
            bar_color = bar_color.replace("0.8", "0.6")
        self._bar.setStyleSheet(f"background: {bar_color}; border-radius: 1px;")

    def mousePressEvent(self, event):
        self.clicked.emit(self._index)
        super().mousePressEvent(event)


class AppRulesDialog(QDialog):
    """Dialog to configure per-application pause/run rules."""

    STYLE = LIQUID_GLASS_DIALOG_STYLE + """
        QScrollArea { border: none; background: transparent; }
        QScrollBar:vertical {
            width: 4px; background: transparent;
        }
        QScrollBar::handle:vertical {
            background: rgba(255,255,255,25); border-radius: 2px;
            min-height: 30px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QLineEdit {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 10px;
            padding: 10px 16px;
            color: rgba(255,255,255,0.9);
            font-size: 18px; }"
            font-family: 'Consolas', 'SF Mono', monospace;
        }
        QLineEdit:focus {
            border-color: rgba(255,255,255,0.5);
            background: rgba(255,255,255,0.08);
            selection-background-color: rgba(255,255,255,0.4);
        }
        QComboBox {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 10px;
            padding: 10px 16px;
            color: rgba(255,255,255,0.9);
            font-size: 18px; }"
            min-width: 140px;
        }
        QComboBox::drop-down { border: none; width: 28px; }
        QComboBox::down-arrow {
            width: 0; height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid rgba(255,255,255,0.6);
        }
        QComboBox QAbstractItemView {
            background: #1e1e20;
            color: rgba(255,255,255,0.9);
            border: 1px solid rgba(255,255,255,0.15);
            selection-background-color: rgba(255,255,255,0.25);
            padding: 4px;
        }
    """

    def __init__(self, rules, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分类规则管理")
        self.setFixedSize(780, 680)
        self.rules = [dict(r) for r in rules]
        self._selected_idx = -1
        self._cards = []
        self._search_text = ""
        try:
            self.setStyleSheet(self.STYLE)
        except Exception:
            pass
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("background: transparent;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(28, 24, 28, 16)
        h_lay.setSpacing(16)

        icon_wrap = QFrame()
        icon_wrap.setFixedSize(52, 52)
        icon_wrap.setStyleSheet(
            "background: rgba(255,255,255,0.06); //"
            "stop:0 rgba(255,255,255,0.6), stop:1 rgba(255,255,255,0.4));"
            "border: 1px solid rgba(255,255,255,0.15); border-radius: 16px;"
        )
        icon_inner = QLabel("✧")
        icon_inner.setAlignment(Qt.AlignCenter)
        icon_inner.setStyleSheet("font-size: 32px; background: transparent; border: none;")
        icon_lay = QVBoxLayout(icon_wrap)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        icon_lay.addWidget(icon_inner)
        h_lay.addWidget(icon_wrap)

        txt_lay = QVBoxLayout()
        txt_lay.setSpacing(4)
        txt_lay.setContentsMargins(0, 0, 0, 0)
        title = QLabel("分类规则管理")
        title.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 20px; font-weight: 500; background: transparent;")
        subtitle = QLabel("当指定应用运行时，自动覆盖全局回放设置")
        subtitle.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 13px; background: transparent;")
        txt_lay.addWidget(title)
        txt_lay.addWidget(subtitle)
        h_lay.addLayout(txt_lay, 1)

        root.addWidget(header)

        # Divider
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 1px;")
        div1.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 1px;")
        div1.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 1px;")
        root.addWidget(div1)

        # Content
        content = QFrame()
        content.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(28, 16, 28, 10)
        c_lay.setSpacing(10)

        # Stats bar
        stats_lay = QHBoxLayout()
        stats_lay.setSpacing(8)
        stats_lay.setContentsMargins(0, 0, 0, 0)

        self._stat_pause = self._make_stat_chip("rgba(220,160,80,180)", "暂停", 0)
        self._stat_run = self._make_stat_chip("rgba(100,180,120,180)", "保持运行", 0)
        self._stat_total = self._make_stat_chip(None, "共", 0, suffix="条规则")

        stats_lay.addWidget(self._stat_pause)
        stats_lay.addWidget(self._stat_run)
        stats_lay.addWidget(self._stat_total)
        stats_lay.addStretch()
        c_lay.addLayout(stats_lay)

        # Search filter
        search_frame = QFrame()
        search_frame.setStyleSheet(
            "background: rgba(255,255,255,0.05);"
            "border: 1px solid rgba(255,255,255,0.12);"
            "border-radius: 12px;"
        )
        search_lay = QHBoxLayout(search_frame)
        search_lay.setContentsMargins(14, 0, 14, 0)
        search_lay.setSpacing(10)
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 18px; background: transparent; border: none; color: rgba(255,255,255,0.3);")
        search_lay.addWidget(search_icon)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("搜索进程名或规则...")
        self._search_edit.setStyleSheet(
            "background: transparent; border: none; padding: 10px 4px;"
            "color: rgba(255,255,255,0.85); font-size: 18px; font-family: 'Consolas', 'SF Mono', monospace;"
        )
        self._search_edit.textChanged.connect(self._on_search)
        search_lay.addWidget(self._search_edit, 1)
        c_lay.addWidget(search_frame)

        # Rule list (scroll area)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setMaximumHeight(240)

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 6, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_container)
        c_lay.addWidget(self._scroll, 1)

        # Add section
        add_frame = QFrame()
        add_frame.setStyleSheet(
            "background: rgba(255,255,255,0.03);"
            "border: 1px dashed rgba(255,255,255,0.12);"
            "border-radius: 16px;"
        )
        add_lay = QVBoxLayout(add_frame)
        add_lay.setContentsMargins(18, 16, 18, 16)
        add_lay.setSpacing(12)

        add_header = QHBoxLayout()
        add_header.setSpacing(10)
        add_icon = QLabel("+")
        add_icon.setFixedSize(28, 28)
        add_icon.setAlignment(Qt.AlignCenter)
        add_icon.setStyleSheet(
            "background: rgba(255,255,255,0.06);"
            "border: 1px solid rgba(255,255,255,0.1);"
            "border-radius: 8px; color: rgba(255,255,255,0.9); font-size: 24px; font-weight: bold;"
        )
        add_label = QLabel("添加新规则")
        add_label.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 13px; background: transparent;")
        add_header.addWidget(add_icon)
        add_header.addWidget(add_label)
        add_header.addStretch()
        add_lay.addLayout(add_header)

        add_row = QHBoxLayout()
        add_row.setSpacing(12)
        self._exe_edit = QLineEdit()
        self._exe_edit.setPlaceholderText("输入进程名，如 chrome.exe")
        add_row.addWidget(self._exe_edit, 1)

        self._behavior_combo = QComboBox()
        self._behavior_combo.addItems(["⏸ 暂停", "▶ 保持运行"])
        add_row.addWidget(self._behavior_combo)

        add_btn = QPushButton("＋ 添加")
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        add_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.06); //"
            "stop:0 rgba(255,255,255,0.7), stop:1 rgba(255,255,255,0.5));"
            "border: 1px solid rgba(255,255,255,0.6); border-radius: 10px;"
            "padding: 10px 28px; color: rgba(255,255,255,0.95); font-size: 18px; font-weight: 500; }"
            "QPushButton:hover { background: rgba(255,255,255,0.06); //"
            "stop:0 rgba(255,255,255,0.9), stop:1 rgba(255,255,255,0.7));"
            "border-color: rgba(255,255,255,0.8); }"
        )
        add_btn.clicked.connect(self._add_rule)
        add_row.addWidget(add_btn)
        add_lay.addLayout(add_row)
        c_lay.addWidget(add_frame)

        root.addWidget(content)

        # Divider 2
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 1px;")
        div2.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 1px;")
        div2.setStyleSheet("background: rgba(255,255,255,0.03); border-radius: 1px;")
        root.addWidget(div2)

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background: transparent;")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(28, 16, 28, 20)

        del_btn = QPushButton("🗑 删除选中")
        del_btn.setCursor(QCursor(Qt.PointingHandCursor))
        del_btn.setStyleSheet(
            "QPushButton { background: rgba(255,100,100,0.1);"
            "border: 1px solid rgba(255,100,100,0.3);"
            "border-radius: 12px; padding: 10px 24px; color: rgba(255,255,255,0.5); font-size: 18px; }"
            "QPushButton:hover { background: rgba(255,100,100,0.2);"
            "border-color: rgba(255,100,100,0.5);"
            "color: rgba(255,140,140,0.9); }"
        )
        del_btn.clicked.connect(self._del_rule)
        f_lay.addWidget(del_btn)

        f_lay.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
        cancel_btn.setStyleSheet(
            "QPushButton { background: transparent;"
            "border: 1px solid rgba(255,255,255,0.15);"
            "border-radius: 12px; padding: 10px 24px; color: rgba(255,255,255,0.5); font-size: 18px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.06);"
            "color: rgba(255,255,255,0.8); }"
        )
        cancel_btn.clicked.connect(self.reject)
        f_lay.addWidget(cancel_btn)

        ok_btn = QPushButton("✓ 确定")
        ok_btn.setCursor(QCursor(Qt.PointingHandCursor))
        ok_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.06); //"
            "stop:0 rgba(255,255,255,0.8), stop:1 rgba(255,255,255,0.6));"
            "border: 1px solid rgba(255,255,255,0.7); border-radius: 10px;"
            "padding: 10px 28px; color: rgba(255,255,255,0.95); font-size: 18px; font-weight: 500; }"
            "QPushButton:hover { background: rgba(255,255,255,0.06); //"
            "stop:0 rgba(255,255,255,1), stop:1 rgba(255,255,255,0.8));"
            "border-color: rgba(255,255,255,0.9); }"
        )
        ok_btn.clicked.connect(self.accept)
        f_lay.addWidget(ok_btn)

        root.addWidget(footer)

    def _make_stat_chip(self, dot_color, label, count, suffix=None):
        frame = QFrame()
        frame.setStyleSheet(
            "background: rgba(255,255,255,0.06);"
            "border: 1px solid rgba(255,255,255,0.1);"
            "border-radius: 20px;"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 8, 16, 8)
        lay.setSpacing(8)

        if dot_color:
            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background: {dot_color}; border-radius: 4px;")
            lay.addWidget(dot)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 13px; background: transparent;")
        lay.addWidget(lbl)

        num = QLabel(str(count))
        num.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 14px; font-weight: 500; background: transparent;")
        lay.addWidget(num)

        if suffix:
            sfx = QLabel(suffix)
            sfx.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 13px; background: transparent;")
            lay.addWidget(sfx)

        return frame

    def _update_stats(self):
        pause_count = sum(1 for r in self.rules if r["behavior"] == "pause")
        run_count = len(self.rules) - pause_count
        self._stat_pause.layout().itemAt(2).widget().setText(str(pause_count))
        self._stat_run.layout().itemAt(2).widget().setText(str(run_count))
        self._stat_total.layout().itemAt(1).widget().setText(str(len(self.rules)))

    def _on_search(self, text):
        self._search_text = text.strip().lower()
        self._refresh_list()

    def _refresh_list(self):
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()
        self._selected_idx = -1

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filtered = [(i, r) for i, r in enumerate(self.rules)
                     if not self._search_text or self._search_text in r["exe"].lower()]

        if not filtered:
            empty = QLabel("暂无匹配的规则")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 18px; padding: 28px; background: transparent;")
            self._list_layout.addWidget(empty)
        else:
            for i, r in filtered:
                desc = r.get("description", "")
                card = _RuleCard(i, r["exe"], r["behavior"], description=desc)
                card.clicked.connect(self._on_card_clicked)
                self._list_layout.addWidget(card)
                self._cards.append(card)

        self._list_layout.addStretch()
        self._update_stats()

    def _on_card_clicked(self, index):
        self._selected_idx = index
        for card in self._cards:
            card.set_selected(card._index == index)
        if 0 <= index < len(self.rules):
            r = self.rules[index]
            self._exe_edit.setText(r["exe"])
            beh_text = "⏸ 暂停" if r["behavior"] == "pause" else "▶ 保持运行"
            self._behavior_combo.setCurrentText(beh_text)

    def _add_rule(self):
        exe = self._exe_edit.text().strip().lower()
        if not exe:
            return
        if not exe.endswith(".exe"):
            exe += ".exe"
        combo_text = self._behavior_combo.currentText()
        beh = "pause" if "暂停" in combo_text else "keep_running"
        self.rules.append({"exe": exe, "behavior": beh})
        self._refresh_list()
        if self._cards:
            self._on_card_clicked(len(self.rules) - 1)

    def _del_rule(self):
        if 0 <= self._selected_idx < len(self.rules):
            self.rules.pop(self._selected_idx)
            self._refresh_list()

class SettingsDialog(QDialog):
    """完整设置对话框 — Crystal Glass (琉璃水晶) 风格"""

    SETTINGS_STYLE = """
        QDialog {
            background: qlineargradient(x1:0,y1:0,x2:0.3,y2:1,
                stop:0 #12122a, stop:0.5 #0e0e22, stop:1 #14102a);
            color: rgba(255,255,255,0.9);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 20px;
        }
        QLabel {
            color: rgba(255,255,255,0.8);
            font-size: 13px;
            background: transparent;
        }
        QTabWidget::pane {
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(255,255,255,0.025), stop:1 rgba(255,255,255,0.01));
        }
        QTabBar::tab {
            background: rgba(255,255,255,0.03);
            color: rgba(255,255,255,0.4);
            padding: 8px 18px;
            border: 1px solid rgba(255,255,255,0.04);
            border-bottom: none;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(255,255,255,0.05), stop:1 rgba(255,255,255,0.02));
            color: rgba(255,255,255,0.85);
            border-bottom: 2px solid rgba(255,255,255,0.12);
        }
        QTabBar::tab:hover:!selected {
            background: rgba(255,255,255,0.04);
            color: rgba(255,255,255,0.6);
        }
        QComboBox {
            background: rgba(255,255,255,0.03);
            color: rgba(255,255,255,0.75);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px;
            padding: 6px 12px;
            min-width: 120px;
        }
        QComboBox:hover { border-color: rgba(255,255,255,0.12); }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox::down-arrow {
            width: 0; height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid rgba(255,255,255,0.3);
        }
        QComboBox QAbstractItemView {
            background: #12122a;
            color: rgba(255,255,255,0.8);
            border: 1px solid rgba(255,255,255,0.08);
            selection-background-color: rgba(255,255,255,0.06);
        }
        QSlider::groove:horizontal {
            height: 4px;
            background: rgba(255,255,255,0.06);
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            width: 14px; height: 14px;
            margin: -5px 0;
            background: rgba(255,255,255,0.18);
            border-radius: 7px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        QSlider::sub-page:horizontal {
            background: rgba(255,255,255,0.15);
            border-radius: 2px;
        }
        QRadioButton {
            color: rgba(255,255,255,0.75);
            spacing: 8px;
        }
        QGroupBox {
            font-weight: bold;
            color: rgba(255,255,255,0.6);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            margin-top: 12px;
            padding-top: 16px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
        QPushButton {
            background: rgba(255,255,255,0.04);
            color: rgba(255,255,255,0.75);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px;
            padding: 6px 16px;
            min-width: 60px;
        }
        QPushButton:hover {
            background: rgba(255,255,255,0.06);
            border-color: rgba(255,255,255,0.1);
        }
        QPushButton:pressed {
            background: rgba(255,255,255,0.08);
        }
        QLineEdit {
            background: rgba(255,255,255,0.03);
            color: rgba(255,255,255,0.8);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 8px;
            padding: 7px 10px;
        }
        QLineEdit:focus { border-color: rgba(255,255,255,0.12); }
        QSpinBox {
            background: rgba(255,255,255,0.03);
            color: rgba(255,255,255,0.8);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 6px;
            padding: 4px;
        }
        QCheckBox {
            color: rgba(255,255,255,0.75);
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 16px; height: 16px;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 4px;
            background: rgba(255,255,255,0.03);
        }
        QCheckBox::indicator:checked {
            background: rgba(100,200,150,0.4);
            border-color: rgba(100,200,150,0.3);
        }
        QScrollBar:vertical {
            background: rgba(255,255,255,0.02);
            width: 5px; border-radius: 2px;
        }
        QScrollBar::handle:vertical {
            background: rgba(255,255,255,0.08);
            border-radius: 2px; min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
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

        # Crystal glass window icon
        from PyQt5.QtGui import QPixmap, QPainter, QColor, QRadialGradient, QPen, QIcon
        from PyQt5.QtCore import Qt
        px = QPixmap(64, 64)
        px.fill(Qt.transparent)
        painter = QPainter(px)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # Outer glow
        g1 = QRadialGradient(32, 32, 30)
        g1.setColorAt(0, QColor(120, 160, 255, 40))
        g1.setColorAt(1, QColor(120, 160, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(g1)
        painter.drawEllipse(2, 2, 60, 60)
        # Diamond shape
        from PyQt5.QtGui import QPolygonF
        from PyQt5.QtCore import QPointF
        diamond = QPolygonF([
            QPointF(32, 6), QPointF(58, 32), QPointF(32, 58), QPointF(6, 32)
        ])
        g2 = QRadialGradient(32, 28, 22)
        g2.setColorAt(0, QColor(200, 210, 255, 200))
        g2.setColorAt(0.5, QColor(140, 160, 220, 150))
        g2.setColorAt(1, QColor(80, 100, 160, 100))
        painter.setBrush(g2)
        painter.setPen(QPen(QColor(180, 200, 255, 120), 1.5))
        painter.drawPolygon(diamond)
        # Inner highlight
        inner = QPolygonF([
            QPointF(32, 14), QPointF(48, 32), QPointF(32, 50), QPointF(16, 32)
        ])
        g3 = QRadialGradient(30, 26, 14)
        g3.setColorAt(0, QColor(255, 255, 255, 80))
        g3.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(g3)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(inner)
        painter.end()
        self.setWindowIcon(QIcon(px))

        self._data = dict(data) if data else {}
        self.result_settings = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Crystal refraction line at top ──
        crystal_line = QFrame()
        crystal_line.setFixedHeight(1)
        crystal_line.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 transparent, stop:0.35 rgba(255,255,255,0.12), "
            "stop:0.5 rgba(255,255,255,0.18), stop:0.65 rgba(255,255,255,0.12), "
            "stop:1 transparent);"
        )
        layout.addWidget(crystal_line)

        # ── Title area ──
        title_frame = QFrame()
        title_frame.setStyleSheet("background: transparent;")
        tf_layout = QHBoxLayout(title_frame)
        tf_layout.setContentsMargins(24, 18, 24, 10)
        tf_layout.setSpacing(12)

        icon_lbl = QLabel("✧")
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(255,255,255,0.06), stop:1 rgba(255,255,255,0.02));"
            "border: 1px solid rgba(255,255,255,0.1);"
            "border-radius: 12px;"
            "font-size: 17px; color: rgba(255,255,255,0.5);"
        )
        tf_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t1 = QLabel("设置")
        t1.setStyleSheet(
            "font-size: 18px; font-weight: 600; color: rgba(255,255,255,0.85);"
            "background: transparent; letter-spacing: 0.5px;"
        )
        title_col.addWidget(t1)
        t2 = QLabel("回放 · 品质 · 常规 · 关于")
        t2.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.28); background: transparent;")
        title_col.addWidget(t2)
        tf_layout.addLayout(title_col)
        tf_layout.addStretch()
        layout.addWidget(title_frame)

        # ── Separator ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 transparent, stop:0.1 rgba(255,255,255,0.05), "
            "stop:0.5 rgba(255,255,255,0.05), stop:0.9 rgba(255,255,255,0.05), "
            "stop:1 transparent);"
        )
        layout.addWidget(sep)

        # ── Tabs ──
        tabs_content = QFrame()
        tabs_content.setStyleSheet("background: transparent;")
        tabs_layout = QVBoxLayout(tabs_content)
        tabs_layout.setContentsMargins(14, 8, 14, 0)
        tabs_layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(self._build_playback_tab(), "回放")
        tabs.addTab(self._build_quality_tab(), "品质")
        tabs.addTab(self._build_general_tab(), "常规")
        tabs.addTab(self._build_about_tab(), "关于")
        tabs_layout.addWidget(tabs)
        layout.addWidget(tabs_content, 1)

        # ── Bottom buttons ──
        btn_bar = QFrame()
        btn_bar.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(24, 6, 24, 16)
        btn_layout.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedHeight(32)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(
            "QPushButton {"
            "background: transparent;"
            "border: 1px solid rgba(255,255,255,0.05);"
            "border-radius: 7px;"
            "color: rgba(255,255,255,0.3); font-size: 12px; padding: 0 18px;"
            "}"
            "QPushButton:hover { background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.5); }"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton("确定")
        btn_ok.setFixedHeight(32)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet(
            "QPushButton {"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(255,255,255,0.06), stop:1 rgba(255,255,255,0.03));"
            "border: 1px solid rgba(255,255,255,0.1);"
            "border-radius: 7px;"
            "color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 500; padding: 0 22px;"
            "}"
            "QPushButton:hover { background: rgba(255,255,255,0.08); }"
        )
        btn_ok.clicked.connect(self._on_accept)
        btn_layout.addWidget(btn_ok)
        layout.addWidget(btn_bar)

    # ── 回放标签 ──────────────────────────────────────────────
    def _build_playback_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("回放")
        header.setStyleSheet("font-size:14px; font-weight:600; color:rgba(255,255,255,0.75);")
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
        header.setStyleSheet("font-size:14px; font-weight:600; color:rgba(255,255,255,0.75);")
        layout.addWidget(header)

        # 画质预设
        preset_frame = QFrame()
        preset_frame.setStyleSheet(
            "QFrame {"
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 rgba(255,255,255,0.025), stop:1 rgba(255,255,255,0.01));"
            "border: 1px solid rgba(255,255,255,0.05);"
            "border-radius: 10px;"
            "}"
        )
        preset_frame_layout = QVBoxLayout(preset_frame)
        preset_label = QLabel("画质预设")
        preset_label.setStyleSheet("font-weight: 600; color: rgba(255,255,255,0.6);")
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
        dlg = AppRulesDialog(current_rules, self)
        if dlg.exec_() == QDialog.Accepted:
            self._data["app_rules"] = dlg.rules

    # ── 常规标签 ──────────────────────────────────────────────
    def _build_general_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("常规")
        header.setStyleSheet("font-size:14px; font-weight:600; color:rgba(255,255,255,0.75);")
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
        name_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: rgba(255,255,255,0.85);")
        name_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_lbl)

        ver_lbl = QLabel(f"版本 {APP_VERSION}")
        ver_lbl.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.35);")
        ver_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver_lbl)

        desc_lbl = QLabel("一款现代化的桌面组织工具，支持动态壁纸效果。")
        desc_lbl.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.45);")
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
        features.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 12px; line-height: 1.6;")
        features.setAlignment(Qt.AlignCenter)
        layout.addWidget(features)

        layout.addSpacing(12)

        # Keyboard shortcuts reference
        shortcuts = QLabel(
            "<b style='color: rgba(255,255,255,0.65);'>快捷键</b><br>"
            "<span style='color: rgba(255,255,255,0.35); font-size: 12px;'>"
            "Ctrl+Shift+O　　全局显示/隐藏<br>"
            "Ctrl+N　　　　　新建分类<br>"
            "Ctrl+O　　　　　打开设置<br>"
            "Ctrl+E　　　　　显示/隐藏窗口<br>"
            "ESC　　　　　　 关闭菜单/退出移动模式"
            "</span>"
        )
        shortcuts.setTextFormat(Qt.RichText)
        shortcuts.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 rgba(255,255,255,0.025), stop:1 rgba(255,255,255,0.01));"
            "padding: 10px 16px; border-radius: 8px;"
            "border: 1px solid rgba(255,255,255,0.04);"
        )
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
