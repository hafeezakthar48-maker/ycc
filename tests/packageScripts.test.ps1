$ErrorActionPreference = "Stop"

function Assert-PathExists {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  if (-not (Test-Path $Path)) {
    throw "Missing file: $Path"
  }
}

function Assert-FileContains {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [Parameter(Mandatory = $true)]
    [string]$Pattern
  )

  $content = Get-Content -Raw $Path
  if ($content -notmatch $Pattern) {
    throw "File $Path does not contain required pattern: $Pattern"
  }
}

function Assert-PowerShellParses {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  $null = [scriptblock]::Create((Get-Content -Raw $Path))
}

function Assert-ParamIsFirstStatement {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  $firstStatement = Get-Content $Path |
    Where-Object { $_.Trim() -ne "" -and -not $_.Trim().StartsWith("#") } |
    Select-Object -First 1

  if ($firstStatement.Trim() -ne "param(") {
    throw "Param block must be the first statement in $Path"
  }
}

Assert-PathExists "scripts/build-windows-package.ps1"
Assert-PathExists "scripts/installer/install.ps1"
Assert-PathExists "scripts/installer/uninstall.ps1"
Assert-PathExists "scripts/installer/launch.ps1"

Assert-FileContains "scripts/build-windows-package.ps1" "pyinstaller"
Assert-FileContains "scripts/build-windows-package.ps1" "ChinaFinanceAIAssistant-Windows-x64.zip"
Assert-FileContains "scripts/installer/install.ps1" "ChinaFinanceAIAssistant.exe"
Assert-FileContains "scripts/installer/install.ps1" "CreateShortcut"
Assert-FileContains "scripts/installer/uninstall.ps1" "Remove-Item"
Assert-FileContains "scripts/installer/launch.ps1" "ChinaFinanceAIAssistant.exe"

Assert-PowerShellParses "scripts/build-windows-package.ps1"
Assert-PowerShellParses "scripts/installer/install.ps1"
Assert-PowerShellParses "scripts/installer/uninstall.ps1"
Assert-PowerShellParses "scripts/installer/launch.ps1"

Assert-ParamIsFirstStatement "scripts/build-windows-package.ps1"
Assert-ParamIsFirstStatement "scripts/installer/install.ps1"
Assert-ParamIsFirstStatement "scripts/installer/uninstall.ps1"

Write-Host "Windows package script tests passed"
