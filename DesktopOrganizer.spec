# -*- mode: python ; coding: utf-8 -*-
"""DesktopOrganizer PyInstaller spec — --onedir mode for stability"""

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('constants.py', '.'),
        ('wallpaper_engine.py', '.'),
        ('icon_utils.py', '.'),
        ('widgets.py', '.'),
        ('dialogs.py', '.'),
        ('organizer.py', '.'),
    ],
    hiddenimports=[
        'PyQt5.QtMultimedia',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtCore',
        'ctypes',
        'ctypes.wintypes',
        'winreg',
        'json',
        'threading',
        'math',
        'random',
        'time',
        'tempfile',
        'shutil',
        'pathlib',
        'os',
        'sys',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test',
        'matplotlib', 'numpy', 'pandas',
        'scipy', 'PIL', 'cv2',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DesktopOrganizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DesktopOrganizer',
)
