@echo off
setlocal

python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --name MetaIphonePhoto --collect-all pillow_heif gui.py

echo.
echo Build complete. The executable is in dist\MetaIphonePhoto.exe
pause
