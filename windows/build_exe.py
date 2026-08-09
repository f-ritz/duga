"""
Build the Duga Windows application for installer packaging (pure tkinter + ttk + tray).

Version: 1.1.1 'Berkut-AM'

This builds a folder-based distribution (not a single standalone EXE) suitable for
the Inno Setup installer.

Usage (from project root on Windows):
    python windows\build_exe.py

Also installs pywin32 if missing (needed for tray).

Output: dist\Duga\ (folder with Duga.exe and dependencies)
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUI_SCRIPT = PROJECT_ROOT / "windows" / "duga_gui.py"
DIST_DIR = PROJECT_ROOT / "dist"
ICON = PROJECT_ROOT / "icon.ico"
if not ICON.exists():
    ICON = PROJECT_ROOT / "radar.ico"
if ICON.exists():
    print(f"Found icon: {ICON}")
VERSION_INFO = PROJECT_ROOT / "windows" / "version_info.txt"

print('Building Duga 1.1.1 \'Berkut-AM\' (onedir for installer)...')

# Ensure pywin32 is available for tray (harmless if already present)
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32", "--quiet"])
except Exception:
    print("Warning: Could not install pywin32. Tray may not work in EXE.")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onedir",
    "--windowed",
    "--name", "Duga",
    "--hidden-import", "tkinter",
    "--hidden-import", "tkinter.ttk",
    "--hidden-import", "win32gui",
    "--hidden-import", "win32con",
    "--hidden-import", "win32api",
    "--hidden-import", "duga",
    "--hidden-import", "duga.config",
    "--hidden-import", "duga.main",
    "--hidden-import", "duga.gather",
    "--hidden-import", "duga.llm",
    "--hidden-import", "duga.history",
    "--hidden-import", "duga.telegram_bot",
    "--hidden-import", "apify_client",
    "--hidden-import", "apify_client.client",
    "--collect-data", "trafilatura",
    "--collect-data", "apify_client",
    str(GUI_SCRIPT),
]

if VERSION_INFO.exists():
    cmd += ["--version-file", str(VERSION_INFO)]
    print(f"Using version info: {VERSION_INFO} (1.1.1 Berkut-AM)")
else:
    print("No version_info.txt found.")

if ICON.exists():
    cmd += ["--icon", str(ICON)]
    cmd += ["--add-data", f"{ICON};."]
    print(f"Using icon: {ICON}")
else:
    print("No icon.ico or radar.ico found — put one in the project root for EXE + tray icon.")

result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

if result.returncode == 0:
    print('\n✅ Build succeeded! 1.1.1 \'Berkut-AM\'')
    dist_folder = DIST_DIR / "Duga"
    print(f"   Distribution folder: {dist_folder}")
    print("   This is for the installer (not a portable standalone EXE).")
    print("   Now compile windows\\DugaInstaller.iss with Inno Setup.")
else:
    print("\n❌ Build failed.")
    sys.exit(1)
