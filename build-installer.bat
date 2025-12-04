@echo off
echo ========================================
echo T2 Tarkov Toolbox - Installer Build
echo ========================================
echo.

echo [1/4] Setting up MSVC environment...
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
echo [OK] MSVC configured
echo.

echo [2/4] Building frontend...
call npm run build
if %errorLevel% NEQ 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b 1
)
echo [OK] Frontend built
echo.

echo [3/4] Building Tauri with NSIS installer...
echo This will create a Windows installer (.exe)
echo This may take several minutes...
call npm run tauri build
if %errorLevel% NEQ 0 (
    echo [ERROR] Installer build failed!
    pause
    exit /b 1
)
echo [OK] Installer built
echo.

echo [4/4] Locating installer...
echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Installer location:
for /f "delims=" %%i in ('dir /s /b "src-tauri\target\release\bundle\nsis\*.exe" 2^>nul') do echo   %%i
echo.
echo Standalone executable:
echo   src-tauri\target\release\t2-tarkov-toolbox.exe
echo.
echo ========================================
pause
