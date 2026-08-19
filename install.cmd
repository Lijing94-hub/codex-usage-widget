@echo off
setlocal
set "SOURCE_DIR=%~dp0"
if not exist "%SOURCE_DIR%CodexVision.exe" if exist "%SOURCE_DIR%dist\CodexVision\CodexVision.exe" set "SOURCE_DIR=%SOURCE_DIR%dist\CodexVision"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1" -SourceDir "%SOURCE_DIR%"
if errorlevel 1 (
  echo.
  echo Codex Vision installation failed.
  pause
  exit /b 1
)

exit /b 0
