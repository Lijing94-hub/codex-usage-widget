@echo off
setlocal
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Vision.lnk"
if exist "%LINK%" del "%LINK%"
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Usage Widget.lnk" del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Codex Usage Widget.lnk"
echo Removed startup shortcut if it existed.
pause
