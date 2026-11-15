# One-time setup for Windows (PowerShell).
# Run from inside the project folder (the folder that contains run_all.py):
#     Set-ExecutionPolicy -Scope CurrentUser RemoteSigned      # once per computer
#     .\setup_windows.ps1

function Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Check($what) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $what (exit code $LASTEXITCODE). See HOW_TO_RUN_AR.md, section 'Common problems'." -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path ".\run_all.py")) {
    Write-Host "run_all.py not found. cd into the folder that contains run_all.py and try again." -ForegroundColor Red
    exit 1
}

Step "Checking for Python 3.12"
& py -3.12 --version
if ($LASTEXITCODE -ne 0) {
    Step "Python 3.12 not found - trying 'py install 3.12'"
    & py install 3.12
    & py -3.12 --version
    Check "Python 3.12 is required. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH')"
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Step "Creating virtual environment .venv (Python 3.12)"
    & py -3.12 -m venv .venv
    Check "creating .venv"
}
$vpy = ".\.venv\Scripts\python.exe"

Step "Upgrading pip"
& $vpy -m pip install --upgrade pip
Check "pip upgrade"

Step "Installing PyTorch (CPU build is fine)"
& $vpy -m pip install torch
Check "torch install"

Step "Installing project requirements"
& $vpy -m pip install -r requirements.txt
Check "requirements install"

Step "Running unit tests"
& $vpy -m pytest -q tests
Check "unit tests"

Write-Host ""
Write-Host "Setup finished. Next:  .\run_windows.ps1 smoke" -ForegroundColor Green
