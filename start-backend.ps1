$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  Write-Host "Creating Python virtual environment..."
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m venv .venv
  } elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m venv .venv
  } else {
    throw "Python launcher not found. Please install Python 3 first."
  }
}

Write-Host "Installing backend dependencies..."
& $VenvPython -m pip install -r requirements.txt

Write-Host "Running Django migrations..."
& $VenvPython manage.py migrate

Write-Host "Starting Django backend at http://127.0.0.1:8000/"
& $VenvPython manage.py runserver 127.0.0.1:8000
