@echo off
setlocal
set "APP_DIR=%~dp0"
set "BUILD_VENV=%APP_DIR%.venv-build"
set "PY=%BUILD_VENV%\Scripts\python.exe"
set "DIST_DIR=%APP_DIR%dist\CodexVision"
set "ZIP_PATH=%APP_DIR%dist\CodexVision-Windows.zip"

tasklist /FI "IMAGENAME eq CodexVision.exe" 2>nul | find /I "CodexVision.exe" >nul
if not errorlevel 1 (
  echo Codex Vision is running. Close it before rebuilding the Windows package.
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo Could not find Python on PATH. Install Python 3.10+ first.
  exit /b 1
)

if not exist "%PY%" (
  python -m venv "%BUILD_VENV%"
  if errorlevel 1 exit /b 1
)

"%PY%" -m pip install --disable-pip-version-check -r "%APP_DIR%requirements-dev.txt"
if errorlevel 1 exit /b 1

"%PY%" -m ruff check "%APP_DIR%codex_usage_widget.py" "%APP_DIR%tools\generate_docs_assets.py"
if errorlevel 1 exit /b 1

"%PY%" -m py_compile "%APP_DIR%codex_usage_widget.py" "%APP_DIR%tools\generate_docs_assets.py"
if errorlevel 1 exit /b 1

"%PY%" "%APP_DIR%codex_usage_widget.py" --test --include-ui
if errorlevel 1 exit /b 1

"%PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name CodexVision ^
  --icon "%APP_DIR%assets\codex-usage.ico" ^
  --version-file "%APP_DIR%assets\windows-version-info.txt" ^
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
echo %DIST_DIR%\CodexVision.exe
echo %ZIP_PATH%
