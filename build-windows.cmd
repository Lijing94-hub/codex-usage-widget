@echo off
setlocal
set "APP_DIR=%~dp0"
set "BUILD_VENV=%APP_DIR%.venv-build"
set "PY=%BUILD_VENV%\Scripts\python.exe"
set "DIST_DIR=%APP_DIR%dist\CodexUsageWidget"
set "ZIP_PATH=%APP_DIR%dist\CodexUsageWidget-Windows.zip"

where py >nul 2>nul
if errorlevel 1 (
  echo Could not find the Python launcher. Install Python 3.10+ first.
  exit /b 1
)

if not exist "%PY%" (
  py -3 -m venv "%BUILD_VENV%"
  if errorlevel 1 exit /b 1
)

"%PY%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

"%PY%" -m pip install -r "%APP_DIR%requirements-dev.txt"
if errorlevel 1 exit /b 1

"%PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name CodexUsageWidget ^
  --icon "%APP_DIR%assets\codex-usage.ico" ^
  --add-data "%APP_DIR%assets;assets" ^
  "%APP_DIR%codex_usage_widget.py"
if errorlevel 1 exit /b 1

copy /Y "%APP_DIR%README.md" "%DIST_DIR%\README.md" >nul
copy /Y "%APP_DIR%LICENSE" "%DIST_DIR%\LICENSE" >nul
copy /Y "%APP_DIR%install-startup-exe.cmd" "%DIST_DIR%\install-startup.cmd" >nul
copy /Y "%APP_DIR%uninstall-startup.cmd" "%DIST_DIR%\uninstall-startup.cmd" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force"
if errorlevel 1 exit /b 1

echo Built:
echo %DIST_DIR%\CodexUsageWidget.exe
echo %ZIP_PATH%
