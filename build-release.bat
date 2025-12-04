@echo off
echo ========================================
echo T2 Tarkov Toolbox - Release Builder
echo ========================================
echo.

echo [1/4] Setting up MSVC environment...
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
echo [OK] MSVC environment configured
echo.

echo [2/4] Building frontend...
call npm run build
if %errorLevel% NEQ 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b 1
)
echo [OK] Frontend built successfully
echo.

echo [3/4] Building Tauri application (Release mode)...
echo This may take several minutes...
call npm run tauri build -- --no-bundle
if %errorLevel% NEQ 0 (
    echo [ERROR] Tauri build failed!
    pause
    exit /b 1
)
echo [OK] Tauri build completed
echo.

echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Your executable is located at:
echo   src-tauri\target\release\t2-tarkov-toolbox.exe
echo.
echo IMPORTANT: To run with administrator privileges:
echo   1. Double-click: launch-as-admin.vbs
echo      OR
echo   2. Right-click t2-tarkov-toolbox.exe and select "Run as administrator"
echo.
echo ========================================
echo.
pause
