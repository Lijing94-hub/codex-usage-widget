[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\CodexVision"),
    [string]$DesktopDir = [Environment]::GetFolderPath("DesktopDirectory"),
    [string]$ProgramsDir = [Environment]::GetFolderPath("Programs"),
    [string]$StartupDir = [Environment]::GetFolderPath("Startup"),
    [switch]$KeepApplicationFiles
)

$ErrorActionPreference = "Stop"
$installPath = [IO.Path]::GetFullPath($InstallDir).TrimEnd("\")
$defaultInstallPath = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Programs\CodexVision")).TrimEnd("\")

Get-Process -Name "CodexVision" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($installPath, [StringComparison]::OrdinalIgnoreCase) } |
    Stop-Process -Force

@(
    (Join-Path $DesktopDir "Codex Vision.lnk"),
    (Join-Path $DesktopDir "Codex Usage Widget.lnk"),
    (Join-Path $DesktopDir "Codex Limit.lnk"),
    (Join-Path $ProgramsDir "Codex Vision.lnk"),
    (Join-Path $StartupDir "Codex Vision Launcher.lnk"),
    (Join-Path $StartupDir "Codex Vision.lnk"),
    (Join-Path $StartupDir "Codex Usage Widget.lnk")
) | ForEach-Object {
    if (Test-Path -LiteralPath $_) {
        Remove-Item -LiteralPath $_ -Force
    }
}

if (-not $KeepApplicationFiles -and (Test-Path -LiteralPath $installPath)) {
    if (-not $installPath.Equals($defaultInstallPath, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a non-default install directory: $installPath"
    }
    Remove-Item -LiteralPath $installPath -Recurse -Force
}

Write-Host "Codex Vision was uninstalled. Local usage settings were preserved."
