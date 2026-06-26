# Duga Windows GUI + Installer (EXE) — 1.0.0 "Berkut-M"

**Duga 1.0.0 "Berkut-M"**

Pure `tkinter` + `ttk` GUI matching your PFR Reactor Sizer style.

Version codename: Berkut-M

## New Features (this update)
- Proper application icon (`icon.ico`)
- **Minimize to system tray** when you click the X (instead of exiting)
- Full tray icon with menu (Show, Run Briefing Now, Exit)
- Double-click tray icon restores the window
- `--minimized` flag for clean startup
- Real Windows installer (Inno Setup) so it appears in "Apps & features" like a normal program

## Running
```powershell
python windows\duga_gui.py
python windows\duga_gui.py --minimized
```

## Building for the Installer
```powershell
python windows\build_exe.py
```
Requires: `pip install pywin32` (for tray) + PyInstaller.

This produces a folder distribution at `dist\Duga\` (PyInstaller onedir mode) intended to be packaged by the installer.

**Note:** This is no longer a portable standalone single-file EXE. The build is specifically for proper Windows installation via the installer.

## Creating the Installer (recommended for distribution)

1. Download & install **Inno Setup** (free): https://jrsoftware.org/isinfo.php
2. Open `windows\DugaInstaller.iss`
3. Press **Compile** (or F9)
4. The installer `DugaSetup-1.0.0-Berkut-M.exe` will be created in `dist\`

The installer will:
- Install to `%LocalAppData%\Duga`
- Create Start Menu shortcuts
- Add to Startup (so it launches minimized with tray on login)
- Register proper uninstaller
- Support easy in-place updates: running a newer installer will automatically (silently) uninstall the old version first. You can simply double-click the new DugaSetup-*.exe while an older version is installed — it will update cleanly over the top.

## Tray Behavior
- Click X → hides to tray (app keeps running)
- Double-click tray icon → shows main window
- Right-click tray → menu with "Show", "Run Briefing Now", "Exit"
- Use tray "Exit" to fully quit

## Icon
Place `icon.ico` (recommended: 256×256 with 16/32/48/256 sizes) in the project root before building.
The same file is used for:
- EXE icon
- Window title bar / taskbar
- System tray icon

## Persistence
After running the installer + allowing startup shortcut, Duga will start automatically when you log in and live in the tray.

You can still use the `duga` CLI tool (if installed via pip) — it shares the same config files.
