@echo off
setlocal
set "APP_DIR=%~dp0"
set "EXE=%APP_DIR%CodexVision.exe"
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Vision.lnk"
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Usage Widget.lnk" del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Usage Widget.lnk"

if not exist "%EXE%" (
  echo Could not find CodexVision.exe in:
  echo %APP_DIR%
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut($env:LINK); $shortcut.TargetPath=$env:EXE; $shortcut.WorkingDirectory=$env:APP_DIR; $shortcut.IconLocation=$env:EXE; $shortcut.Description='Codex Vision desktop usage widget'; $shortcut.Save()"
echo Installed startup shortcut:
echo %LINK%
pause
