@echo off
echo ============================================
echo  Building AC Sprite Slicer EXE
echo ============================================
echo.

:: Build single-file EXE with PyInstaller
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "AC Sprite Slicer" ^
    --add-data "batch_auto_slicer.py;." ^
    --add-data "tile_categorizer.py;." ^
    --add-data "generate_ue5_meshes.py;." ^
    --add-data "sprite_slicer.py;." ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    app.py

echo.
if exist "dist\AC Sprite Slicer.exe" (
    echo ============================================
    echo  SUCCESS! EXE built at:
    echo  dist\AC Sprite Slicer.exe
    echo ============================================
) else (
    echo  BUILD FAILED - check output above
)
pause
