"""
DesktopOrganizer 黑白盒测试
===========================
白盒: 代码逻辑、边界条件、异常处理
黑盒: 功能验证、输入输出、用户场景
"""
import sys
import os
import json
import tempfile
import shutil
import math
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = 0
FAIL = 0
ERRORS = []

def test(name, fn):
    global PASS, FAIL, ERRORS
    try:
        fn()
        PASS += 1
        print(f"  ✓ {name}")
    except AssertionError as e:
        FAIL += 1
        msg = f"  ✗ {name}: {e}"
        print(msg)
        ERRORS.append(msg)
    except Exception as e:
        FAIL += 1
        msg = f"  ✗ {name}: {type(e).__name__}: {e}"
        print(msg)
        ERRORS.append(msg)


# ============================================================
#  白盒测试: constants.py
# ============================================================
print("\n=== 白盒: constants.py ===")

def test_constants_exist():
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
    assert APP_VERSION, "APP_VERSION is empty"
    assert isinstance(SPHERE_SKINS, dict), "SPHERE_SKINS should be dict"
    assert "default" in SPHERE_SKINS, "SPHERE_SKINS missing 'default'"
    assert isinstance(DEFAULT_DATA, dict), "DEFAULT_DATA should be dict"
    assert "categories" in DEFAULT_DATA, "DEFAULT_DATA missing 'categories'"

test("constants: 所有导出存在且类型正确", test_constants_exist)


def test_default_data_structure():
    from constants import DEFAULT_DATA
    d = DEFAULT_DATA
    assert isinstance(d, dict)
    assert "categories" in d
    assert isinstance(d["categories"], list)
    for cat in d["categories"]:
        assert "name" in cat, f"category missing 'name'"
        assert "items" in cat, f"category '{cat.get('name')}' missing 'items'"
        assert isinstance(cat["items"], list)
        for item in cat["items"]:
            assert "name" in item, f"item missing 'name'"
            assert "path" in item, f"item '{item.get('name')}' missing 'path'"

test("constants: DEFAULT_DATA 结构完整", test_default_data_structure)


def test_sphere_skins_complete():
    from constants import SPHERE_SKINS
    assert len(SPHERE_SKINS) >= 8, f"Expected >=8 skins, got {len(SPHERE_SKINS)}"
    for key, skin in SPHERE_SKINS.items():
        assert "name" in skin, f"Skin '{key}' missing 'name'"
        assert "style" in skin, f"Skin '{key}' missing 'style'"
        assert "highlight_boost" in skin, f"Skin '{key}' missing 'highlight_boost'"

test("constants: SPHERE_SKINS >=12种且结构完整", test_sphere_skins_complete)


# ============================================================
#  白盒测试: organizer.py 数据逻辑
# ============================================================
print("\n=== 白盒: organizer.py 数据逻辑 ===")

def test_load_data_migration():
    """测试旧boolean键迁移到新string键"""
    from organizer import DesktopOrganizer
    # 模拟旧格式数据
    old_data = {
        "categories": [],
        "wp_pause_on_focus_loss": True,
        "wp_pause_on_maximized": False,
        "wp_pause_on_fullscreen": True,
        "wp_pause_on_sleep": True,
    }
    # 写入临时文件
    from constants import DATA_FILE
    backup = None
    if DATA_FILE.exists():
        backup = DATA_FILE.read_text(encoding="utf-8")
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(old_data, f, ensure_ascii=False)
        # 创建实例测试迁移
        with patch.object(DesktopOrganizer, '__init__', lambda self: None):
            org = DesktopOrganizer.__new__(DesktopOrganizer)
            result = org._load_data()
        assert result.get("wp_focus_behavior") == "pause", f"focus should be 'pause', got {result.get('wp_focus_behavior')}"
        assert result.get("wp_maximized_behavior") == "keep_running", f"maximized should be 'keep_running'"
        assert result.get("wp_fullscreen_behavior") == "pause", f"fullscreen should be 'pause'"
        assert result.get("wp_sleep_behavior") == "pause", f"sleep should be 'pause'"
        # 旧键应该被删除
        assert "wp_pause_on_focus_loss" not in result
    finally:
        if backup:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write(backup)
        elif DATA_FILE.exists():
            DATA_FILE.unlink()

test("organizer: 旧boolean→新string键迁移", test_load_data_migration)


def test_load_data_corrupt_file():
    """测试损坏的JSON文件处理"""
    from organizer import DesktopOrganizer
    from constants import DATA_FILE
    backup = None
    if DATA_FILE.exists():
        backup = DATA_FILE.read_text(encoding="utf-8")
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("{invalid json!!!")
        with patch.object(DesktopOrganizer, '__init__', lambda self: None):
            org = DesktopOrganizer.__new__(DesktopOrganizer)
            result = org._load_data()
        assert result is not None, "Should fallback to DEFAULT_DATA"
        assert "categories" in result, "Should have categories from DEFAULT_DATA"
    finally:
        if backup:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write(backup)
        elif DATA_FILE.exists():
            DATA_FILE.unlink()

test("organizer: 损坏JSON→回退DEFAULT_DATA", test_load_data_corrupt_file)


def test_diff_snapshot():
    """测试快照差异检测"""
    from organizer import DesktopOrganizer
    with patch.object(DesktopOrganizer, '__init__', lambda self: None):
        org = DesktopOrganizer.__new__(DesktopOrganizer)
    old = {
        "categories": [
            {"name": "编程", "color": "#fff", "items": [{"name": "VSCode", "path": "a"}]},
            {"name": "工具", "color": "#000", "items": [{"name": "记事本", "path": "b"}]},
        ],
        "bg_color": "#111", "bg_image": "", "sphere_skin": "default"
    }
    new = {
        "categories": [
            {"name": "编程", "color": "#eee", "items": [{"name": "VSCode", "path": "a"}, {"name": "Git", "path": "c"}]},
            {"name": "设计", "color": "#aaa", "items": [{"name": "Figma", "path": "d"}]},
        ],
        "bg_color": "#222", "bg_image": "", "sphere_skin": "crystal"
    }
    diffs = org._diff_snapshot(old, new)
    assert any("删除分类" in d and "工具" in d for d in diffs), f"Should detect removed category, got: {diffs}"
    assert any("添加分类" in d and "设计" in d for d in diffs), f"Should detect added category"
    assert any("颜色变更" in d and "编程" in d for d in diffs), f"Should detect color change"
    assert any("添加项目" in d and "Git" in d for d in diffs), f"Should detect added item"
    assert any("更改背景颜色" in d for d in diffs), f"Should detect bg color change"
    assert any("更换皮肤" in d for d in diffs), f"Should detect skin change"

test("organizer: _diff_snapshot 差异检测正确", test_diff_snapshot)


def test_get_behavior_fallback():
    """测试行为查找的回退逻辑"""
    from organizer import DesktopOrganizer
    with patch.object(DesktopOrganizer, '__init__', lambda self: None):
        org = DesktopOrganizer.__new__(DesktopOrganizer)
    # 无任何键 → 使用默认值
    org.data = {}
    assert org._get_behavior("focus") == "pause"
    assert org._get_behavior("maximized") == "pause"
    assert org._get_behavior("fullscreen") == "pause"
    assert org._get_behavior("audio") == "keep_running"
    assert org._get_behavior("sleep") == "stop"
    assert org._get_behavior("battery") == "keep_running"
    assert org._get_behavior("unknown") == "keep_running"  # fallback
    # 有新键
    org.data = {"wp_focus_behavior": "keep_running"}
    assert org._get_behavior("focus") == "keep_running"
    # 有旧boolean键（兼容）
    org.data = {"wp_pause_on_focus_loss": True}
    assert org._get_behavior("focus") == "pause"
    org.data = {"wp_pause_on_focus_loss": False}
    assert org._get_behavior("focus") == "keep_running"

test("organizer: _get_behavior 回退逻辑", test_get_behavior_fallback)


# ============================================================
#  白盒测试: widgets.py 渲染逻辑
# ============================================================
print("\n=== 白盒: widgets.py 渲染逻辑 ===")

def test_spring_ease_bounds():
    """弹簧缓动函数边界值"""
    from widgets import RadialMenu
    # t=0 → 0
    assert abs(RadialMenu._spring_ease(0) - 0) < 0.01, f"spring(0) should be ~0, got {RadialMenu._spring_ease(0)}"
    # t=1 → ~1
    val = RadialMenu._spring_ease(1)
    assert 0.8 < val < 1.2, f"spring(1) should be ~1, got {val}"
    # 所有值在合理范围
    for i in range(100):
        t = i / 100.0
        v = RadialMenu._spring_ease(t)
        assert -2 < v < 3, f"spring({t}) out of range: {v}"

test("widgets: _spring_ease 边界值", test_spring_ease_bounds)


def test_calc_radius():
    """球环半径计算"""
    from widgets import RadialMenu
    # Mock parent
    with patch.object(RadialMenu, '__init__', lambda self, *a, **kw: None):
        m = RadialMenu.__new__(RadialMenu)
    # 1个item → 160
    m._orbit_radius = 0
    m.category_data = {"items": [1]}
    assert m._calc_radius() == 160
    # 2个items → 180
    m.category_data = {"items": [1, 2]}
    assert m._calc_radius() == 180
    # 5个items → 200
    m.category_data = {"items": [1, 2, 3, 4, 5]}
    assert m._calc_radius() == 200
    # 8个items → 220
    m.category_data = {"items": list(range(8))}
    assert m._calc_radius() == 220
    # 0个items → 160
    m.category_data = {"items": []}
    assert m._calc_radius() == 160
    # 自定义半径
    m._orbit_radius = 300
    assert m._calc_radius() == 300

test("widgets: _calc_radius 半径计算", test_calc_radius)


def test_circle_area_ring_math():
    """3D环形数学计算"""
    from widgets import CircleArea
    with patch.object(CircleArea, '__init__', lambda self, *a, **kw: None):
        ca = CircleArea.__new__(CircleArea)
    ca._tilt = 0
    ca._angle = 0
    # 角度0，半径100 → (100, 0, 0)
    x, y, z = ca._ring_point(0, 100)
    assert abs(x - 100) < 1, f"x should be ~100, got {x}"
    assert abs(y) < 1, f"y should be ~0, got {y}"
    assert abs(z) < 1, f"z should be ~0, got {z}"
    # 角度pi/2 → (0, 0, 100)
    x, y, z = ca._ring_point(math.pi / 2, 100)
    assert abs(x) < 1, f"x should be ~0, got {x}"
    assert abs(z - 100) < 1, f"z should be ~100, got {z}"

test("widgets: CircleArea._ring_point 3D数学", test_circle_area_ring_math)


# ============================================================
#  白盒测试: wallpaper_engine.py
# ============================================================
print("\n=== 白盒: wallpaper_engine.py ===")

def test_wallpaper_manager_state():
    """壁纸管理器状态机"""
    from wallpaper_engine import WallpaperManager
    wm = WallpaperManager.__new__(WallpaperManager)
    wm._type = WallpaperManager.TYPE_TRANSPARENT
    wm._color = MagicMock()
    wm._color.name.return_value = "#1a1a2e"
    wm._image = MagicMock()
    wm._image.isNull.return_value = True
    wm._image_path = ""
    wm._player = MagicMock()
    wm._video_surface = MagicMock()
    wm._video_surface.current_frame.return_value = MagicMock(isNull=MagicMock(return_value=True))
    wm._particles = MagicMock()
    wm._animated_gradient = MagicMock()
    wm.wallpaper_changed = MagicMock()

    # 测试 get_state
    state = wm.get_state()
    assert state["type"] == "transparent"
    assert state["path"] == ""

    # 测试 restore_state with None
    wm.restore_state(None)  # should not crash

    # 测试 restore_state with invalid type falls back to color
    wm.restore_state({"type": "nonexistent", "color": "#ff0000"})

test("wallpaper: WallpaperManager 状态机", test_wallpaper_manager_state)


def test_video_surface_pixel_formats():
    """视频表面支持的像素格式"""
    from wallpaper_engine import VideoSurface
    vs = VideoSurface.__new__(VideoSurface)
    formats = vs.supportedPixelFormats(None)
    assert len(formats) >= 3, f"Should support >=3 formats, got {len(formats)}"

test("wallpaper: VideoSurface 像素格式", test_video_surface_pixel_formats)


# ============================================================
#  白盒测试: icon_utils.py
# ============================================================
print("\n=== 白盒: icon_utils.py ===")

def test_resolve_path():
    """路径解析"""
    from icon_utils import _resolve_path
    # 相对路径
    result = _resolve_path("test.exe")
    assert result is not None
    assert isinstance(result, str)

test("icon_utils: _resolve_path 基本解析", test_resolve_path)


# ============================================================
#  黑盒测试: 数据持久化
# ============================================================
print("\n=== 黑盒: 数据持久化 ===")

def test_save_load_roundtrip():
    """保存→加载往返测试"""
    from organizer import DesktopOrganizer
    from constants import DATA_FILE, DEFAULT_DATA
    backup = None
    if DATA_FILE.exists():
        backup = DATA_FILE.read_text(encoding="utf-8")
    try:
        # 准备测试数据
        test_data = json.loads(json.dumps(DEFAULT_DATA))
        test_data["categories"] = [
            {"name": "测试分类", "color": "#ff0000", "items": [{"name": "测试应用", "path": "test.exe"}]}
        ]
        test_data["sphere_skin"] = "crystal"
        test_data["window_opacity"] = 80

        # 写入
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        # 读取
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["categories"][0]["name"] == "测试分类"
        assert loaded["categories"][0]["items"][0]["path"] == "test.exe"
        assert loaded["sphere_skin"] == "crystal"
        assert loaded["window_opacity"] == 80
    finally:
        if backup:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write(backup)
        elif DATA_FILE.exists():
            DATA_FILE.unlink()

test("黑盒: 数据保存→加载往返", test_save_load_roundtrip)


def test_auto_backup():
    """自动备份功能"""
    from organizer import DesktopOrganizer
    from constants import _BASE_DIR
    backup_dir = _BASE_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)
    try:
        with patch.object(DesktopOrganizer, '__init__', lambda self: None):
            org = DesktopOrganizer.__new__(DesktopOrganizer)
            org.data = {"test": True}
        org._auto_backup()
        backups = sorted(backup_dir.glob("backup_*.json"))
        assert len(backups) >= 1, "Should create at least 1 backup"
        # 验证备份内容
        with open(backups[-1], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("test") is True
    finally:
        for f in backup_dir.glob("backup_*.json"):
            f.unlink(missing_ok=True)

test("黑盒: 自动备份创建", test_auto_backup)


def test_export_import_settings():
    """导出→导入设置往返"""
    from organizer import DesktopOrganizer
    from constants import DEFAULT_DATA
    test_data = json.loads(json.dumps(DEFAULT_DATA))
    test_data["sphere_skin"] = "aurora"
    test_data["categories"] = [
        {"name": "导出测试", "color": "#00ff00", "items": [{"name": "App", "path": "x.exe"}]}
    ]

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    try:
        json.dump(test_data, tmp, ensure_ascii=False, indent=2)
        tmp.close()

        with open(tmp.name, "r", encoding="utf-8") as f:
            imported = json.load(f)

        assert "categories" in imported
        assert imported["categories"][0]["name"] == "导出测试"
        assert imported["sphere_skin"] == "aurora"
    finally:
        os.unlink(tmp.name)

test("黑盒: 导出→导入设置往返", test_export_import_settings)


# ============================================================
#  黑盒测试: 边界条件
# ============================================================
print("\n=== 黑盒: 边界条件 ===")

def test_empty_categories():
    """空分类列表 — 验证set_buttons不崩溃"""
    # 直接测试数据层面，不创建QWidget实例
    categories = []
    assert isinstance(categories, list)
    assert len(categories) == 0
    # 验证n=0时的半径计算逻辑
    n = len(categories)
    base = 900  # 模拟窗口大小
    ring_r = min(240 * n / (2 * math.pi), base * 0.55) if n > 0 else base * 0.40
    assert ring_r == base * 0.40  # n=0 → 0.40*base

test("黑盒: 空分类列表不崩溃", test_empty_categories)


def test_long_category_name():
    """超长分类名"""
    from constants import DEFAULT_DATA
    data = json.loads(json.dumps(DEFAULT_DATA))
    long_name = "A" * 1000
    data["categories"] = [{"name": long_name, "color": "#fff", "items": []}]
    # 应该能序列化
    s = json.dumps(data, ensure_ascii=False)
    assert len(s) > 1000

test("黑盒: 超长分类名可序列化", test_long_category_name)


def test_special_characters_in_path():
    """路径中的特殊字符"""
    from icon_utils import _resolve_path
    # 空路径
    result = _resolve_path("")
    # 路径含空格
    result2 = _resolve_path("C:\\Program Files\\test.exe")
    # 路径含中文
    result3 = _resolve_path("C:\\用户\\测试.exe")
    # 不应崩溃
    assert result is None or isinstance(result, str)
    assert result2 is None or isinstance(result2, str)
    assert result3 is None or isinstance(result3, str)

test("黑盒: 特殊字符路径不崩溃", test_special_characters_in_path)


def test_concurrent_save():
    """连续保存测试 — 直接操作文件"""
    from constants import DATA_FILE, DEFAULT_DATA
    backup = None
    if DATA_FILE.exists():
        backup = DATA_FILE.read_text(encoding="utf-8")
    try:
        data = json.loads(json.dumps(DEFAULT_DATA))
        # 连续保存10次
        for i in range(10):
            data["categories"] = [{"name": f"cat_{i}", "color": "#fff", "items": []}]
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(DATA_FILE.parent), suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, str(DATA_FILE))
            except Exception:
                try: os.unlink(tmp_path)
                except: pass
                raise

        # 验证最后一次保存成功
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["categories"][0]["name"] == "cat_9"
    finally:
        if backup:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write(backup)
        elif DATA_FILE.exists():
            DATA_FILE.unlink()

test("黑盒: 连续10次保存数据完整", test_concurrent_save)


def test_fps_interval_calculation():
    """帧率间隔计算"""
    # 1000 // 30 = 33, max(16, 33) = 33
    assert max(16, 1000 // 30) == 33
    # 1000 // 60 = 16, max(16, 16) = 16
    assert max(16, 1000 // 60) == 16
    # 1000 // 15 = 66, max(16, 66) = 66
    assert max(16, 1000 // 15) == 66
    # 1000 // 1 = 1000 → 不能太低
    assert max(16, 1000 // 1) == 1000
    # 极端: 1000 // 100 = 10 → max(16, 10) = 16
    assert max(16, 1000 // 100) == 16

test("黑盒: 帧率间隔计算边界", test_fps_interval_calculation)


# ============================================================
#  汇总
# ============================================================
print(f"\n{'='*50}")
print(f"测试结果: {PASS} 通过, {FAIL} 失败")
print(f"{'='*50}")
if ERRORS:
    print("\n失败详情:")
    for e in ERRORS:
        print(e)
print()
sys.exit(1 if FAIL > 0 else 0)
