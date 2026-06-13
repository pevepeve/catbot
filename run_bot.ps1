[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment is missing. Run .\deploy_windows.ps1 first."
}

Push-Location $ProjectRoot
try {
    & $VenvPython "bot.py"
}
finally {
    Pop-Location
}
