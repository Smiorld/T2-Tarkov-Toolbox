# T2 Tarkov Toolbox - Development Mode
# Usage: Right-click and "Run with PowerShell" or "Run as administrator"

# CRITICAL: Change to script directory (fixes admin mode issue)
Set-Location $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "T2 Tarkov Toolbox - Development Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "[OK] Running with Administrator privileges" -ForegroundColor Green
} else {
    Write-Host "[INFO] Running without admin privileges" -ForegroundColor Yellow
    Write-Host "[INFO] Filter features may show permission errors" -ForegroundColor Yellow
}
Write-Host ""

# Show current directory
Write-Host "Working directory: $PWD" -ForegroundColor Gray
Write-Host ""

# Set MSVC environment
Write-Host "Setting up MSVC environment..." -ForegroundColor Gray
$vcvarsPath = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if (Test-Path $vcvarsPath) {
    cmd /c "`"$vcvarsPath`" >nul 2>&1 && set" | ForEach-Object {
        if ($_ -match "^(.*?)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], [System.EnvironmentVariableTarget]::Process)
        }
    }
    Write-Host "[OK] MSVC environment configured" -ForegroundColor Green
} else {
    Write-Host "[WARNING] MSVC not found, continuing anyway..." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "Starting Tauri dev server..." -ForegroundColor Gray
Write-Host "- Frontend: http://localhost:1420" -ForegroundColor Gray
Write-Host "- Hot reload enabled (modify code to see changes)" -ForegroundColor Gray
Write-Host "- Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Run npm command
npm run tauri dev

Write-Host ""
Write-Host "Dev server stopped" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to close..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
