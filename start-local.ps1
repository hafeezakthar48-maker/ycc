$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = "C:\Python314\python.exe"

if (-not (Test-Path $python)) {
  throw "未找到 Python：$python"
}

if (-not (Test-Path (Join-Path $backend ".venv"))) {
  & $python -m venv (Join-Path $backend ".venv")
}

$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e "${backend}[dev]"

Push-Location $frontend
try {
  if (-not (Test-Path "node_modules")) {
    cmd.exe /c npm install
    if ($LASTEXITCODE -ne 0) {
      throw "npm install 失败"
    }
  }
}
finally {
  Pop-Location
}

Start-Process -WindowStyle Hidden -FilePath $venvPython -ArgumentList @(
  "-m", "uvicorn", "app.main:app",
  "--host", "127.0.0.1",
  "--port", "8000",
  "--app-dir", $backend
)

Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList @(
  "/c", "npm run dev -- --host 127.0.0.1 --port 5173"
) -WorkingDirectory $frontend

Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"
Write-Host "后端：http://127.0.0.1:8000/health"
Write-Host "前端：http://127.0.0.1:5173"
