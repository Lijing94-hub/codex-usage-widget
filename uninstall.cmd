@echo off
setlocal
set "UNINSTALL_SCRIPT=%~dp0uninstall-windows.ps1"
cd /d "%TEMP%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%UNINSTALL_SCRIPT%"
if errorlevel 1 (
  echo.
  echo Codex Vision uninstall failed.
  pause
  exit /b 1
)

exit /b 0
