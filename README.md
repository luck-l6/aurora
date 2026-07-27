# DesktopOrganizer 桌面收纳

> 银河星空背景 + 液态玻璃UI + 3D球环分类

桌面收纳是一个现代化的桌面应用管理工具，将你的应用按分类组织成3D球环，悬浮在银河星空背景上。

![Version](https://img.shields.io/badge/version-1.6.0-blue)
![Python](https://img.shields.io/badge/python-3.12+-green)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-purple)

---

## 功能特性

### 核心功能
- **3D球环分类** — 应用按分类排列在可旋转的3D球环上
- **银河星空背景** — 紫蓝粉星云 + 200颗静态星 + 30颗闪烁星
- **液态玻璃UI** — 白银色调，半透明毛玻璃效果
- **全局热键** — `Ctrl+Shift+O` 快速显示/隐藏

### 壁纸模式
- **图片壁纸** — 支持 PNG/JPG/BMP/GIF
- **视频壁纸** — 支持 MP4/AVI（自动循环）
- **纯色/透明** — 纯色背景或完全透明
- **粒子效果** — 动态粒子动画
- **动态渐变** — 渐变色动画背景

### 12种球体皮肤
默认、磨砂、霓虹、宝石、星球、水滴、水晶球、泡泡、极光、哑光、黑曜石、翡翠

### 其他功能
- **番茄钟** — 25分钟工作 + 5分钟休息
- **系统监控** — CPU/内存/磁盘实时显示
- **分类规则** — 按应用自动暂停/继续壁纸
- **自动备份** — 每10次保存自动备份
- **导入/导出** — JSON格式设置备份
- **开机自启** — Windows注册表自启动

---

## 快速开始

### 方式一：运行源码

```bash
# 安装依赖
pip install PyQt5

# 运行
python main.py
```

### 方式二：运行exe

1. 下载 `dist/DesktopOrganizer/` 目录
2. 双击 `DesktopOrganizer.exe`

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+O` | 显示/隐藏主窗口 |
| `ESC` | 退出移动模式 |
| 双击托盘图标 | 显示/隐藏 |

---

## 项目结构

```
DesktopOrganizer/
├── main.py              # 入口文件
├── organizer.py         # 主应用类
├── widgets.py           # UI组件 (球环/按钮/监控/番茄钟)
├── dialogs.py           # 对话框 (设置/规则/皮肤)
├── wallpaper_engine.py  # 壁纸引擎 (图片/视频/粒子)
├── constants.py         # 常量 (颜色/样式/皮肤)
├── icon_utils.py        # 图标工具
├── test黑白盒.py        # 黑白盒测试 (21个)
├── DesktopOrganizer.spec # PyInstaller配置
└── icon.ico             # 应用图标
```

---

## 打包exe

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包 (onedir模式，更稳定)
pyinstaller DesktopOrganizer.spec --noconfirm

# 输出在 dist/DesktopOrganizer/
```

---

## 开发

### 运行测试

```bash
python test黑白盒.py
```

### Git版本管理

```bash
git log --oneline  # 查看版本历史
```

当前版本: v1.6.0 (共15+次提交)

---

## 技术栈

- **Python 3.12+**
- **PyQt5** — GUI框架
- **ctypes** — Windows API调用 (桌面嵌入/热键)
- **PyInstaller** — 打包分发

---

## 许可

个人项目，仅供学习使用。
