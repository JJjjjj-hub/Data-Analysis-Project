$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendRoot = Join-Path $Root "frontend"
$CacheRoot = Join-Path $Root ".npm-cache"
Set-Location $FrontendRoot

if (-not (Test-Path (Join-Path $FrontendRoot "node_modules\.bin\vite.cmd"))) {
  Write-Host "Installing frontend dependencies..."
  if (-not (Test-Path $CacheRoot)) {
    New-Item -ItemType Directory -Path $CacheRoot | Out-Null
  }
  $env:npm_config_cache = $CacheRoot
  npm install --no-audit --no-fund --cache $CacheRoot
}

Write-Host "Starting Vue frontend at http://127.0.0.1:5173/"
npm run dev -- --host 127.0.0.1 --port 5173Remove-Item -Recurse -Force .venv