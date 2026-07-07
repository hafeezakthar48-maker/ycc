param(
  [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\ChinaFinanceAIAssistant"),
  [switch]$RemoveData
)

$ErrorActionPreference = "Stop"

function Assert-SafeUserPath {
  param([string]$Path)
  $resolvedBase = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA)
  $resolvedPath = [System.IO.Path]::GetFullPath($Path)
  if (-not $resolvedPath.StartsWith($resolvedBase, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove a path outside LOCALAPPDATA: $resolvedPath"
  }
}

$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "China Finance AI Assistant.lnk"
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\China Finance AI Assistant"
$dataDir = Join-Path $env:LOCALAPPDATA "ChinaFinanceAIAssistant"

if (Test-Path $desktopShortcut) {
  Remove-Item -LiteralPath $desktopShortcut -Force
}
if (Test-Path $startMenuDir) {
  Remove-Item -LiteralPath $startMenuDir -Recurse -Force
}
if (Test-Path $InstallDir) {
  Assert-SafeUserPath $InstallDir
  Remove-Item -LiteralPath $InstallDir -Recurse -Force
}
if ($RemoveData -and (Test-Path $dataDir)) {
  Assert-SafeUserPath $dataDir
  Remove-Item -LiteralPath $dataDir -Recurse -Force
}

Write-Host "Uninstall completed."
