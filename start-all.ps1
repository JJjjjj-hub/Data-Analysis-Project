$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$BackendScript = Join-Path $Root "start-backend.ps1"
$FrontendScript = Join-Path $Root "start-frontend.ps1"

Start-Process powershell.exe -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  $BackendScript
)

Start-Process powershell.exe -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  $FrontendScript
)

Write-Host "Started backend and frontend in separate PowerShell windows."
