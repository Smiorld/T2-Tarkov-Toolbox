@echo off
setlocal enabledelayedexpansion

echo ========================================
echo T2 Tarkov Toolbox - Portable Build
echo ========================================
echo.

echo [1/5] Setting up MSVC environment...
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
echo [OK] MSVC configured
echo.

echo [2/5] Building frontend...
call npm run build
if %errorLevel% NEQ 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b 1
)
echo [OK] Frontend built
echo.

echo [3/5] Building Rust backend (Release)...
cd src-tauri
cargo build --release
if %errorLevel% NEQ 0 (
    echo [ERROR] Rust build failed!
    cd..
    pause
    exit /b 1
)
cd..
echo [OK] Backend built
echo.

echo [4/5] Creating portable package...
set OUTPUT_DIR=release-portable
if exist %OUTPUT_DIR% rmdir /s /q %OUTPUT_DIR%
mkdir %OUTPUT_DIR%

REM 复制主程序
copy "src-tauri\target\release\t2-tarkov-toolbox.exe" "%OUTPUT_DIR%\" >nul
echo [OK] Copied executable

REM 复制配置文件夹
mkdir "%OUTPUT_DIR%\config"
copy "src-tauri\target\release\config\*.json" "%OUTPUT_DIR%\config\" >nul 2>&1
echo [OK] Created config folder

REM 创建管理员启动器
echo Set UAC = CreateObject("Shell.Application") > "%OUTPUT_DIR%\启动(管理员).vbs"
echo UAC.ShellExecute "t2-tarkov-toolbox.exe", "", "", "runas", 1 >> "%OUTPUT_DIR%\启动(管理员).vbs"
echo [OK] Created admin launcher

REM 创建说明文件
(
echo T2 塔科夫工具箱 - 使用说明
echo ================================
echo.
echo 【启动方式】
echo 1. 推荐: 双击 "启动(管理员).vbs" - 自动请求管理员权限
echo 2. 备选: 右键 "t2-tarkov-toolbox.exe" - 选择"以管理员身份运行"
echo.
echo 【为什么需要管理员权限?】
echo 屏幕滤镜功能需要修改系统 Gamma 设置，这需要管理员权限。
echo.
echo 【配置文件】
echo config\filter_presets.json - 滤镜预设配置
echo.
echo 【版本信息】
echo 版本: 0.1.0
echo 构建日期: %date% %time%
echo.
) > "%OUTPUT_DIR%\使用说明.txt"
echo [OK] Created readme

echo.
echo [5/5] Package complete!
echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Portable package created in: %OUTPUT_DIR%\
echo.
echo Files included:
dir /b "%OUTPUT_DIR%"
echo.
echo Total size:
for /f "tokens=3" %%a in ('dir "%OUTPUT_DIR%" ^| find "个文件"') do set SIZE=%%a
echo %SIZE% bytes
echo.
echo You can now:
echo 1. Test: Double-click "%OUTPUT_DIR%\启动(管理员).vbs"
echo 2. Share: Zip the entire "%OUTPUT_DIR%" folder
echo ========================================
pause
