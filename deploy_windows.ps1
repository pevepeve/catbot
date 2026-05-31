[CmdletBinding()]
param(
    [switch]$StartBot,
    [switch]$ForceRecreateVenv
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[deploy] $Message" -ForegroundColor Cyan
}

function Resolve-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python 3 was not found. Install Python 3.11+ and rerun this script."
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$CommandParts,
        [string]$WorkingDirectory = $ProjectRoot
    )

    Write-Step ("Running: " + ($CommandParts -join " "))
    Push-Location $WorkingDirectory
    try {
        & $CommandParts[0] $CommandParts[1..($CommandParts.Length - 1)]
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code ${LASTEXITCODE}: $($CommandParts -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$EnvExamplePath = Join-Path $ProjectRoot ".env.example"
$EnvPath = Join-Path $ProjectRoot ".env"
$MediaPath = Join-Path $ProjectRoot "media"
$PythonCommand = Resolve-PythonCommand

Write-Step "Project root: $ProjectRoot"

if ($ForceRecreateVenv -and (Test-Path $VenvPath)) {
    Write-Step "Removing existing virtual environment"
    Remove-Item -LiteralPath $VenvPath -Recurse -Force
}

if (-not (Test-Path $VenvPython)) {
    Write-Step "Creating virtual environment"
    Invoke-Checked -CommandParts ($PythonCommand + @("-m", "venv", ".venv"))
}
else {
    Write-Step "Using existing virtual environment"
}

Write-Step "Upgrading pip"
Invoke-Checked -CommandParts @($VenvPython, "-m", "pip", "install", "--upgrade", "pip")

Write-Step "Installing dependencies"
Invoke-Checked -CommandParts @($VenvPython, "-m", "pip", "install", "-r", "requirements.txt")

if (-not (Test-Path $MediaPath)) {
    Write-Step "Creating media directory"
    New-Item -ItemType Directory -Path $MediaPath | Out-Null
}
else {
    Write-Step "Media directory already exists"
}

if ((Test-Path $EnvExamplePath) -and (-not (Test-Path $EnvPath))) {
    Write-Step "Creating .env from .env.example"
    Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
}
elseif (Test-Path $EnvPath) {
    Write-Step ".env already exists"
}
else {
    Write-Step "No .env.example found; skipping .env creation"
}

Write-Host ""
Write-Host "Deployment bootstrap finished." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Edit $EnvPath and fill in API_TOKEN, ADMIN_ID, and DB_FILENAME."
Write-Host "2. Start the bot with .\run_bot.ps1"

if ($StartBot) {
    Write-Step "Starting bot"
    Push-Location $ProjectRoot
    try {
        & $VenvPython "bot.py"
    }
    finally {
        Pop-Location
    }
}
