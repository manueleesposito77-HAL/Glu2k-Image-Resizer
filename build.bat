@echo off
echo === Glu2k-Image-Resizer Build ===
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Building executable with PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
    --name "Glu2k-Image-Resizer" ^
    --icon "icon.ico" ^
    --add-data "icon.ico;." ^
    --hidden-import tkinterdnd2 ^
    image_squeezer.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo Executable: dist\Glu2k-Image-Resizer.exe
echo.
echo To create the installer, run Inno Setup with installer.iss
pause
