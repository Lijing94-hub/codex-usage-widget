[CmdletBinding()]
param(
    [string]$SourceDir = $PSScriptRoot,
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\CodexVision"),
    [string]$DesktopDir = [Environment]::GetFolderPath("DesktopDirectory"),
    [string]$ProgramsDir = [Environment]::GetFolderPath("Programs"),
    [string]$StartupDir = [Environment]::GetFolderPath("Startup"),
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$appName = "Codex Vision"
$appId = "Lijing94.CodexVision"

if (-not (Test-Path -LiteralPath (Join-Path $SourceDir "CodexVision.exe"))) {
    throw "CodexVision.exe was not found in $SourceDir"
}

$sourcePath = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $SourceDir).Path).TrimEnd("\")
$installPath = [IO.Path]::GetFullPath($InstallDir).TrimEnd("\")
$installedExe = Join-Path $installPath "CodexVision.exe"

Get-Process -Name "CodexVision" -ErrorAction SilentlyContinue | Stop-Process -Force

if (-not $sourcePath.Equals($installPath, [StringComparison]::OrdinalIgnoreCase)) {
    New-Item -ItemType Directory -Path $installPath -Force | Out-Null
    & robocopy.exe $sourcePath $installPath /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "Failed to copy Codex Vision into $installPath (robocopy exit code $LASTEXITCODE)."
    }
}

if (-not (Test-Path -LiteralPath $installedExe)) {
    throw "Installed executable is missing: $installedExe"
}

$shortcutSource = @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;

namespace CodexVisionInstaller
{
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    public struct PropertyKey
    {
        public Guid FormatId;
        public UInt32 PropertyId;
    }

    [StructLayout(LayoutKind.Explicit)]
    public struct PropVariant
    {
        [FieldOffset(0)] public UInt16 VariantType;
        [FieldOffset(8)] public IntPtr PointerValue;
    }

    [ComImport]
    [Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPropertyStore
    {
        [PreserveSig] int GetCount(out UInt32 propertyCount);
        [PreserveSig] int GetAt(UInt32 propertyIndex, out PropertyKey key);
        [PreserveSig] int GetValue(ref PropertyKey key, out PropVariant value);
        [PreserveSig] int SetValue(ref PropertyKey key, ref PropVariant value);
        [PreserveSig] int Commit();
    }

    [ComImport]
    [Guid("00021401-0000-0000-C000-000000000046")]
    public class ShellLink
    {
    }

    [ComImport]
    [Guid("000214F9-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IShellLinkW
    {
        [PreserveSig] int GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int pathLength, IntPtr findData, UInt32 flags);
        [PreserveSig] int GetIDList(out IntPtr itemIdList);
        [PreserveSig] int SetIDList(IntPtr itemIdList);
        [PreserveSig] int GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder description, int descriptionLength);
        [PreserveSig] int SetDescription([MarshalAs(UnmanagedType.LPWStr)] string description);
        [PreserveSig] int GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder directory, int directoryLength);
        [PreserveSig] int SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string directory);
        [PreserveSig] int GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder arguments, int argumentsLength);
        [PreserveSig] int SetArguments([MarshalAs(UnmanagedType.LPWStr)] string arguments);
        [PreserveSig] int GetHotkey(out UInt16 hotkey);
        [PreserveSig] int SetHotkey(UInt16 hotkey);
        [PreserveSig] int GetShowCmd(out int showCommand);
        [PreserveSig] int SetShowCmd(int showCommand);
        [PreserveSig] int GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder iconPath, int iconPathLength, out int iconIndex);
        [PreserveSig] int SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string iconPath, int iconIndex);
        [PreserveSig] int SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string path, UInt32 reserved);
        [PreserveSig] int Resolve(IntPtr windowHandle, UInt32 flags);
        [PreserveSig] int SetPath([MarshalAs(UnmanagedType.LPWStr)] string path);
    }

    public static class ShortcutIdentity
    {
        [DllImport("ole32.dll", PreserveSig = true)]
        private static extern int PropVariantClear(ref PropVariant value);

        private static PropertyKey AppIdKey()
        {
            return new PropertyKey {
                FormatId = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),
                PropertyId = 5
            };
        }

        public static void Create(
            string shortcutPath,
            string targetPath,
            string arguments,
            string workingDirectory,
            string description,
            string appId)
        {
            object linkObject = new ShellLink();
            var link = (IShellLinkW)linkObject;
            var store = (IPropertyStore)linkObject;
            var persistFile = (IPersistFile)linkObject;
            Marshal.ThrowExceptionForHR(link.SetPath(targetPath));
            Marshal.ThrowExceptionForHR(link.SetArguments(arguments ?? String.Empty));
            Marshal.ThrowExceptionForHR(link.SetWorkingDirectory(workingDirectory));
            Marshal.ThrowExceptionForHR(link.SetDescription(description));
            Marshal.ThrowExceptionForHR(link.SetIconLocation(targetPath, 0));

            var key = AppIdKey();
            var value = new PropVariant {
                VariantType = 31,
                PointerValue = Marshal.StringToCoTaskMemUni(appId)
            };

            try
            {
                Marshal.ThrowExceptionForHR(store.SetValue(ref key, ref value));
                Marshal.ThrowExceptionForHR(store.Commit());
                persistFile.Save(shortcutPath, true);
            }
            finally
            {
                PropVariantClear(ref value);
                Marshal.FinalReleaseComObject(linkObject);
            }
        }

    }
}
"@

if (-not ("CodexVisionInstaller.ShortcutIdentity" -as [type])) {
    Add-Type -TypeDefinition $shortcutSource -Language CSharp
}

function New-CodexVisionShortcut {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Arguments = ""
    )

    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    [CodexVisionInstaller.ShortcutIdentity]::Create(
        $Path,
        $installedExe,
        $Arguments,
        $installPath,
        "Codex Vision desktop usage widget",
        $appId)
    $shellApplication = New-Object -ComObject Shell.Application
    $shortcutItem = $shellApplication.Namespace((Split-Path -Parent $Path)).ParseName((Split-Path -Leaf $Path))
    $actualAppId = $shortcutItem.ExtendedProperty("System.AppUserModel.ID")
    if ($actualAppId -ne $appId) {
        throw "Failed to set the Codex Vision shortcut identity: $Path (actual: '$actualAppId')"
    }
}

$desktopShortcut = Join-Path $DesktopDir "$appName.lnk"
$programsShortcut = Join-Path $ProgramsDir "$appName.lnk"
$watcherShortcut = Join-Path $StartupDir "Codex Vision Launcher.lnk"

@(
    (Join-Path $StartupDir "Codex Vision.lnk"),
    (Join-Path $StartupDir "Codex Usage Widget.lnk"),
    (Join-Path $DesktopDir "Codex Usage Widget.lnk"),
    (Join-Path $DesktopDir "Codex Limit.lnk")
) | ForEach-Object {
    if (Test-Path -LiteralPath $_) {
        Remove-Item -LiteralPath $_ -Force
    }
}

New-CodexVisionShortcut -Path $desktopShortcut
New-CodexVisionShortcut -Path $programsShortcut
New-CodexVisionShortcut -Path $watcherShortcut -Arguments "--watch-codex"

if (-not $NoLaunch) {
    Start-Process -FilePath $installedExe -ArgumentList "--offer-taskbar-pin" -WorkingDirectory $installPath
    Start-Sleep -Milliseconds 750
    Start-Process -FilePath $installedExe -ArgumentList "--watch-codex" -WorkingDirectory $installPath -WindowStyle Hidden
}

Write-Host "Codex Vision installed successfully."
Write-Host "Desktop shortcut: $desktopShortcut"
Write-Host "Codex-linked startup: $watcherShortcut"
