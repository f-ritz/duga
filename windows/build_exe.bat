@echo off
REM Build standalone Windows EXE for Radar GUI (pure ttk + tray)
REM Requires: pip install pyinstaller pywin32

echo Building Duga (onedir folder dist) for installer ...

python windows\build_exe.py

echo.
echo Done. Distribution in dist\Duga\
echo Now compile windows\DugaInstaller.iss with Inno Setup for a real installer.
pause
