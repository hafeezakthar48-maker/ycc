param(
  [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\ChinaFinanceAIAssistant")
)

$ErrorActionPreference = "Stop"

$packageDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceExe = Join-Path $packageDir "ChinaFinanceAIAssistant.exe"
if (-not (Test-Path $sourceExe)) {
  throw "Package is missing ChinaFinanceAIAssistant.exe"
}

$dataDir = Join-Path $env:LOCALAPPDATA "ChinaFinanceAIAssistant"
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "China Finance AI Assistant.lnk"
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\China Finance AI Assistant"
$startShortcut = Join-Path $startMenuDir "China Finance AI Assistant.lnk"
$uninstallShortcut = Join-Path $startMenuDir "Uninstall China Finance AI Assistant.lnk"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null

Copy-Item -LiteralPath $sourceExe -Destination (Join-Path $InstallDir "ChinaFinanceAIAssistant.exe") -Force
Copy-Item -LiteralPath (Join-Path $packageDir "launch.ps1") -Destination (Join-Path $InstallDir "launch.ps1") -Force
Copy-Item -LiteralPath (Join-Path $packageDir "uninstall.ps1") -Destination (Join-Path $InstallDir "uninstall.ps1") -Force

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($desktopShortcut)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$InstallDir\launch.ps1`""
$shortcut.WorkingDirectory = $InstallDir
$shortcut.IconLocation = Join-Path $InstallDir "ChinaFinanceAIAssistant.exe"
$shortcut.Save()

$shortcut = $shell.CreateShortcut($startShortcut)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$InstallDir\launch.ps1`""
$shortcut.WorkingDirectory = $InstallDir
$shortcut.IconLocation = Join-Path $InstallDir "ChinaFinanceAIAssistant.exe"
$shortcut.Save()

$shortcut = $shell.CreateShortcut($uninstallShortcut)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$InstallDir\uninstall.ps1`""
$shortcut.WorkingDirectory = $InstallDir
$shortcut.IconLocation = Join-Path $InstallDir "ChinaFinanceAIAssistant.exe"
$shortcut.Save()

Write-Host "Install completed: $InstallDir"
Write-Host "User data directory: $dataDir"
