$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppPath = Join-Path $ScriptDir 'app.py'

function Test-Python {
    try {
        $null = Get-Command python -ErrorAction Stop
        python -c "import sys, tkinter; print(sys.version)" | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Install-Python {
    Write-Host 'Python with Tkinter was not found. Installing Python 3...'

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'winget is not available on this PC. Install Python manually from https://www.python.org/downloads/windows/ then run this file again.'
    }

    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements --silent

    $pythonPath = "$env:LocalAppData\Microsoft\WindowsApps"
    if ($env:Path -notlike "*$pythonPath*") {
        $env:Path = "$env:Path;$pythonPath"
    }
}

if (-not (Test-Python)) {
    Install-Python
    Start-Sleep -Seconds 2
}

if (-not (Test-Python)) {
    throw 'Python installation did not complete successfully. Please restart and run again.'
}

Write-Host 'Starting remote assistance app...'
python "$AppPath"
