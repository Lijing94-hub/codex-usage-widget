@echo off
setlocal
set "APP_DIR=%~dp0"
set "EXE=%APP_DIR%CodexUsageWidget.exe"
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Usage Widget.lnk"

if not exist "%EXE%" (
  echo Could not find CodexUsageWidget.exe in:
  echo %APP_DIR%
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut($env:LINK); $shortcut.TargetPath=$env:EXE; $shortcut.WorkingDirectory=$env:APP_DIR; $shortcut.IconLocation=$env:EXE; $shortcut.Description='Codex usage desktop widget'; $shortcut.Save()"
echo Installed startup shortcut:
echo %LINK%
pause
