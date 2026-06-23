# Build single-file Windows EXE for Radar GUI (pure ttk style)
# Run from project root:
#   .\windows\build_exe.ps1

Write-Host "Building Duga (onedir folder) for installer ..."

python windows\build_exe.py

Write-Host ""
Write-Host "Build complete."
Write-Host "Distribution folder → dist\Duga\"
Write-Host "Compile windows\DugaInstaller.iss with Inno Setup for a full installer."