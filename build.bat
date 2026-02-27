@echo off
echo ============================================
echo  Building ac-sprite-slicer EXE
echo ============================================
echo.

:: Build single-file EXE with PyInstaller
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "ac-sprite-slicer" ^
    --add-data "batch_auto_slicer.py;." ^
    --add-data "tile_categorizer.py;." ^
    --add-data "generate_ue5_meshes.py;." ^
    --add-data "sprite_slicer.py;." ^
    --add-data "version.py;." ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    app.py

echo.
if exist "dist\ac-sprite-slicer.exe" (
    echo ============================================
    echo  SUCCESS! EXE built at:
    echo  dist\ac-sprite-slicer.exe
    echo ============================================
) else (
    echo  BUILD FAILED - check output above
)
pause
