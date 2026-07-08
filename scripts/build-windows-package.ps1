param(
  [switch]$SkipInstallerExe
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$output = Join-Path $root "output"
$packageName = "ChinaFinanceAIAssistant-Windows-x64"
$zipFileName = "ChinaFinanceAIAssistant-Windows-x64.zip"
$stage = Join-Path $output $packageName
$pyDist = Join-Path $output "pyinstaller-dist"
$pyBuild = Join-Path $output "pyinstaller-build"
$zipPath = Join-Path $output $zipFileName
$installerExePath = Join-Path $output "$packageName-Setup.exe"

function Assert-LastExitCode {
  param([string]$StepName)
  if ($LASTEXITCODE -ne 0) {
    throw "$StepName failed with exit code $LASTEXITCODE"
  }
}

function Invoke-Npm {
  param([string]$Arguments)
  cmd.exe /c "npm $Arguments"
  Assert-LastExitCode "npm $Arguments"
}

function New-IExpressInstaller {
  param(
    [string]$SourceStage,
    [string]$TargetExe
  )

  $iexpress = Get-Command iexpress.exe -ErrorAction SilentlyContinue
  if (-not $iexpress) {
    Write-Warning "iexpress.exe not found. Skipping single-file setup generation."
    return
  }

  $iexpressRoot = Join-Path $env:TEMP "ChinaFinanceAIAssistantIExpress"
  $iexpressSource = Join-Path $iexpressRoot "source"
  $iexpressTarget = Join-Path $iexpressRoot "$packageName-Setup.exe"
  if (Test-Path $iexpressRoot) {
    Remove-Item -LiteralPath $iexpressRoot -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path $iexpressSource | Out-Null
  Copy-Item -Path (Join-Path $SourceStage "*") -Destination $iexpressSource -Recurse -Force

  $files = Get-ChildItem -Path $iexpressSource -File | Sort-Object Name
  $sourceExe = Get-Item (Join-Path $iexpressSource "ChinaFinanceAIAssistant.exe")
  $sourceFileEntries = @()
  $stringEntries = @()
  for ($index = 0; $index -lt $files.Count; $index++) {
    $sourceFileEntries += "%FILE$index%="
    $stringEntries += "FILE$index=$($files[$index].Name)"
  }

  $sedPath = Join-Path $iexpressRoot "installer.sed"
  $sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3

[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=1
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=<None>
AdminQuietInstCmd=%AppLaunched%
UserQuietInstCmd=%AppLaunched%
SourceFiles=SourceFiles

[SourceFiles]
SourceFiles0=$iexpressSource\

[SourceFiles0]
$($sourceFileEntries -join "`r`n")

[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$iexpressTarget
FriendlyName=China Finance AI Assistant
AppLaunched=ChinaFinanceAIAssistant.exe
$($stringEntries -join "`r`n")
"@
  Set-Content -Path $sedPath -Encoding ASCII -Value $sed

  & $iexpress.Source /N /Q $sedPath
  $deadline = (Get-Date).AddSeconds(20)
  while (-not (Test-Path $iexpressTarget) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
  }
  if (Test-Path $iexpressTarget) {
    $iexpressOutput = Get-Item $iexpressTarget
    if ($iexpressOutput.Length -lt $sourceExe.Length) {
      Write-Warning "IExpress output is smaller than the application exe. Skipping unreliable setup file."
      return
    }
    Copy-Item -LiteralPath $iexpressTarget -Destination $TargetExe -Force
    Write-Host "Generated single-file setup: $TargetExe"
  }
  else {
    Write-Warning "IExpress setup generation failed. Zip package is still available."
  }
}

New-Item -ItemType Directory -Force -Path $output | Out-Null

Push-Location $frontend
try {
  Invoke-Npm "install"
  Invoke-Npm "run build"
}
finally {
  Pop-Location
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
  throw "python was not found. The build machine needs Python 3.12 or later."
}

$venv = Join-Path $backend ".venv"
if (-not (Test-Path $venv)) {
  & $pythonCommand.Source -m venv $venv
  Assert-LastExitCode "python -m venv"
}

$venvPython = Join-Path $venv "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
Assert-LastExitCode "pip install --upgrade pip"
& $venvPython -m pip install -e $backend
Assert-LastExitCode "pip install backend"
& $venvPython -m pip install "pyinstaller>=6.0"
Assert-LastExitCode "pip install pyinstaller"

if (Test-Path $pyDist) {
  Remove-Item -LiteralPath $pyDist -Recurse -Force
}
if (Test-Path $pyBuild) {
  Remove-Item -LiteralPath $pyBuild -Recurse -Force
}

$mainSpecPath = Join-Path $backend "pyinstaller\china-finance-ai-assistant.spec"
$updaterSpecPath = Join-Path $backend "pyinstaller\china-finance-updater.spec"
& $venvPython -m PyInstaller --clean --noconfirm --distpath $pyDist --workpath $pyBuild $mainSpecPath
Assert-LastExitCode "PyInstaller main application"
& $venvPython -m PyInstaller --clean --noconfirm --distpath $pyDist --workpath $pyBuild $updaterSpecPath
Assert-LastExitCode "PyInstaller native updater"

$exe = Get-ChildItem -Path $pyDist -Recurse -Filter "ChinaFinanceAIAssistant.exe" | Select-Object -First 1
if (-not $exe) {
  throw "Could not find PyInstaller output: ChinaFinanceAIAssistant.exe"
}
$updaterExe = Get-ChildItem -Path $pyDist -Recurse -Filter "ChinaFinanceUpdater.exe" | Select-Object -First 1
if (-not $updaterExe) {
  throw "Could not find PyInstaller output: ChinaFinanceUpdater.exe"
}

if (Test-Path $stage) {
  Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item -LiteralPath $exe.FullName -Destination (Join-Path $stage "ChinaFinanceAIAssistant.exe") -Force
Copy-Item -LiteralPath $updaterExe.FullName -Destination (Join-Path $stage "ChinaFinanceUpdater.exe") -Force

$readme = @"
中国财务 AI 助手 Windows x64

启动：
1. 解压本发行包到任意目录。
2. 双击 ChinaFinanceAIAssistant.exe。
3. 程序会打开独立桌面窗口，不需要浏览器地址栏，也不需要目标电脑安装 Python、Node.js、npm 或运行 PowerShell 脚本。

交付说明：
这是便携版独立应用文件。需要创建桌面快捷方式时，可右键 ChinaFinanceAIAssistant.exe 后选择“发送到 > 桌面快捷方式”。

软件本体更新：
ChinaFinanceUpdater.exe 是原生独立更新器，由主程序在安装软件本体更新包时调用；不需要手工运行，也不依赖 PowerShell 脚本。

卸载：
关闭程序后删除解压目录即可。用户数据默认写入本机用户数据目录，避免误删账务演示数据。

数据目录：
%LOCALAPPDATA%\ChinaFinanceAIAssistant
"@
Set-Content -Path (Join-Path $stage "README-INSTALL.txt") -Encoding UTF8 -Value $readme

if (Test-Path $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}
if (Test-Path $installerExePath) {
  Remove-Item -LiteralPath $installerExePath -Force
}
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -Force
Write-Host "Generated zip package: $zipPath"

if (-not $SkipInstallerExe) {
  New-IExpressInstaller -SourceStage $stage -TargetExe $installerExePath
}

Write-Host "Windows package build completed."
