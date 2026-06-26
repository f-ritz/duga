# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('C:\\Users\\Fritz\\Desktop\\code-projects\\radar\\icon.ico', '.')]
datas += collect_data_files('trafilatura')
datas += collect_data_files('apify_client')


a = Analysis(
    ['C:\\Users\\Fritz\\Desktop\\code-projects\\radar\\windows\\duga_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['tkinter', 'tkinter.ttk', 'win32gui', 'win32con', 'win32api', 'duga', 'duga.config', 'duga.main', 'duga.gather', 'duga.llm', 'duga.history', 'duga.telegram_bot', 'apify_client', 'apify_client.client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Duga',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='C:\\Users\\Fritz\\Desktop\\code-projects\\radar\\windows\\version_info.txt',
    icon=['C:\\Users\\Fritz\\Desktop\\code-projects\\radar\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Duga',
)
