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

from constants import APP_VERSION, SPHERE_SKINS, MENU_STYLE, _BASE_DIR, CHANGELOG_FILE


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


class AppRulesDialog(QDialog):
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
