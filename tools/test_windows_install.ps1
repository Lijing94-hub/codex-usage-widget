$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$packageDir = Join-Path $repoRoot "dist\CodexVision"
$testRoot = Join-Path $env:TEMP ("CodexVision-InstallTest-" + [Guid]::NewGuid().ToString("N"))
$installDir = Join-Path $testRoot "App"
$desktopDir = Join-Path $testRoot "Desktop"
$programsDir = Join-Path $testRoot "Programs"
$startupDir = Join-Path $testRoot "Startup"

try {
    & (Join-Path $packageDir "install-windows.ps1") `
        -SourceDir $packageDir `
        -InstallDir $installDir `
        -DesktopDir $desktopDir `
        -ProgramsDir $programsDir `
        -StartupDir $startupDir `
        -NoLaunch

    $installedExe = Join-Path $installDir "CodexVision.exe"
    $desktopShortcut = Join-Path $desktopDir "Codex Vision.lnk"
    $programsShortcut = Join-Path $programsDir "Codex Vision.lnk"
    $watcherShortcut = Join-Path $startupDir "Codex Vision Launcher.lnk"
    @($installedExe, $desktopShortcut, $programsShortcut, $watcherShortcut) | ForEach-Object {
        if (-not (Test-Path -LiteralPath $_)) {
            throw "Expected installation artifact is missing: $_"
        }
    }

    $shell = New-Object -ComObject WScript.Shell
    if (-not $shell.CreateShortcut($desktopShortcut).TargetPath.Equals($installedExe, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Desktop shortcut target is incorrect."
    }
    if ($shell.CreateShortcut($watcherShortcut).Arguments -ne "--watch-codex") {
        throw "Codex-linked launcher arguments are incorrect."
    }

    & (Join-Path $packageDir "uninstall-windows.ps1") `
        -InstallDir $installDir `
        -DesktopDir $desktopDir `
        -ProgramsDir $programsDir `
        -StartupDir $startupDir `
        -KeepApplicationFiles

    @($desktopShortcut, $programsShortcut, $watcherShortcut) | ForEach-Object {
        if (Test-Path -LiteralPath $_) {
            throw "Shortcut was not removed by uninstall: $_"
        }
    }

    Write-Host "Windows install smoke test passed."
}
finally {
    $resolvedTestRoot = [IO.Path]::GetFullPath($testRoot)
    $resolvedTemp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd("\") + "\"
    if ($resolvedTestRoot.StartsWith($resolvedTemp, [StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $resolvedTestRoot)) {
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
