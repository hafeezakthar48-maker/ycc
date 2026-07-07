$ErrorActionPreference = "Stop"

$installDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $installDir "ChinaFinanceAIAssistant.exe"
if (-not (Test-Path $exe)) {
  throw "ChinaFinanceAIAssistant.exe was not found"
}

$env:FINANCE_AI_DATA_DIR = Join-Path $env:LOCALAPPDATA "ChinaFinanceAIAssistant"
New-Item -ItemType Directory -Force -Path $env:FINANCE_AI_DATA_DIR | Out-Null

Start-Process -FilePath $exe -WorkingDirectory $installDir
