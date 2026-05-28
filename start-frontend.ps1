$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendRoot = Join-Path $Root "frontend"
Set-Location $FrontendRoot

if (-not (Test-Path (Join-Path $FrontendRoot "node_modules\.bin\vite.cmd"))) {
  Write-Host "Installing frontend dependencies..."
  npm config set cache "$env:LOCALAPPDATA\npm-cache" --global | Out-Null
  npm install --no-audit --no-fund
}

Write-Host "Starting Vue frontend at http://127.0.0.1:5173/"
npm run dev -- --host 127.0.0.1 --port 5173
