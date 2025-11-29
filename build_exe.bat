@echo off
REM MPDA Terminal Application Build Script
REM Uses PyInstaller to create a single Windows executable

echo ==========================================
echo MPDA Terminal Application Build Script
echo ==========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller. Please install it manually.
        pause
        exit /b 1
    )
)

echo Building MPDA Terminal Application...
echo.

REM Build the main application
pyinstaller --noconsole --onefile --name "MPDA_Terminal" ^
    --add-data "mpda_app;mpda_app" ^
    launcher.py

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Build completed successfully!
echo Executable: dist\MPDA_Terminal.exe
echo ==========================================
echo.

REM Also build the patch tool
echo Building Patch Tool...
pyinstaller --noconsole --onefile --name "MPDA_PatchTool" ^
    apply_patch.pyw

if errorlevel 1 (
    echo.
    echo Patch tool build failed!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo All builds completed!
echo Main app: dist\MPDA_Terminal.exe
echo Patch tool: dist\MPDA_PatchTool.exe
echo ==========================================
pause
