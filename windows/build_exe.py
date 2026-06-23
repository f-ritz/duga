"""
Build a standalone Windows .exe for the Radar GUI (pure tkinter + ttk + tray).

Version: 0.1.0 "Berkut"

Usage (from project root on Windows):
    python windows\build_exe.py

Also installs pywin32 if missing (needed for tray).

Output: dist\RadarBriefing.exe
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUI_SCRIPT = PROJECT_ROOT / "windows" / "radar_gui.py"
DIST_DIR = PROJECT_ROOT / "dist"
ICON = PROJECT_ROOT / "icon.ico"
VERSION_INFO = PROJECT_ROOT / "windows" / "version_info.txt"

print('Building Duga.exe 0.1.0 "Berkut" (ttk style + tray support)...')

# Ensure pywin32 is available for tray (harmless if already present)
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32", "--quiet"])
except Exception:
    print("Warning: Could not install pywin32. Tray may not work in EXE.")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "Duga",
    "--hidden-import", "tkinter",
    "--hidden-import", "tkinter.ttk",
    "--hidden-import", "win32gui",
    "--hidden-import", "win32con",
    "--hidden-import", "win32api",
    "--hidden-import", "radar",
    "--hidden-import", "radar.config",
    "--hidden-import", "radar.main",
    "--hidden-import", "radar.gather",
    "--hidden-import", "radar.llm",
    "--hidden-import", "radar.history",
    "--hidden-import", "radar.telegram_bot",
    str(GUI_SCRIPT),
]

if VERSION_INFO.exists():
    cmd += ["--version-file", str(VERSION_INFO)]
    print(f"Using version info: {VERSION_INFO} (0.1.0 Berkut)")
else:
    print("No version_info.txt found.")

if ICON.exists():
    cmd += ["--icon", str(ICON)]
    cmd += ["--add-data", f"{ICON};."]
    print(f"Using icon: {ICON}")
else:
    print("No icon.ico found — put one in the project root for EXE + tray icon.")

result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

if result.returncode == 0:
    print('\n✅ Build succeeded! 0.1.0 "Berkut"')
    exe = DIST_DIR / "Duga.exe"
    print(f"   EXE: {exe}")
    print("   Now build the installer with Inno Setup using windows\\DugaInstaller.iss")
else:
    print("\n❌ Build failed.")
    sys.exit(1)
