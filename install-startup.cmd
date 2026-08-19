@echo off
setlocal
set "APP_DIR=%~dp0"
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Vision.lnk"
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Usage Widget.lnk" del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Usage Widget.lnk"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut($env:LINK); $shortcut.TargetPath=(Join-Path $env:APP_DIR 'start.cmd'); $shortcut.WorkingDirectory=$env:APP_DIR; $shortcut.IconLocation=(Join-Path $env:APP_DIR 'assets\codex-usage.ico'); $shortcut.Description='Codex Vision desktop usage widget'; $shortcut.Save()"
echo Installed startup shortcut:
echo %LINK%
pause
