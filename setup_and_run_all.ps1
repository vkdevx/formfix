# Setup and run the full FormSaathi stack (backend + frontend) on Windows PowerShell
# Usage:   powershell -ExecutionPolicy Bypass -File .\setup_and_run_all.ps1
# This script works even if the project lives inside a OneDrive folder by copying it
# to a plain location (C:\formsaathi) the first time it runs.

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# 1️⃣ Determine source and target project directories
# ------------------------------------------------------------
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path   # directory where this script lives

# If the source path contains "OneDrive", copy to C:\formsaathi (if not already there)
if ($SourceRoot -match "OneDrive") {
    $TargetRoot = "C:\formsaathi"
    if (-Not (Test-Path $TargetRoot)) {
        Write-Host "Copying project from OneDrive to $TargetRoot ..."
        # Use robocopy for robust copying (mirrors file tree, preserves permissions)
        $null = robocopy $SourceRoot $TargetRoot /MIR /Z /R:2 /W:5 /NFL /NDL /NP /NJH /NJS
        Write-Host "Copy completed."
    } else {
        Write-Host "Target $TargetRoot already exists – using existing copy."
    }
} else {
    $TargetRoot = $SourceRoot
}

# Helper to build absolute paths inside the target project
function Join-Target([string]$sub) { Join-Path $TargetRoot $sub }

# ------------------------------------------------------------
# 2️⃣ Backend setup (virtualenv, pip install)
# ------------------------------------------------------------
$BackendDir = Join-Target "backend"
Set-Location $BackendDir

# Remove any stale .venv that may have bad permissions
if (Test-Path ".venv") {
    Write-Host "Removing existing .venv to avoid permission issues..."
    Remove-Item -Recurse -Force .venv
}

Write-Host "Creating fresh Python virtual environment..."
python -m venv .venv

# Activate the venv (PowerShell activation script)
$activateScript = Join-Path $BackendDir ".venv\Scripts\Activate.ps1"
& $activateScript

Write-Host "Upgrading pip..."
pip install --upgrade pip setuptools wheel

Write-Host "Installing backend dependencies from requirements.txt..."
pip install -r requirements.txt

# ------------------------------------------------------------
# 3️⃣ Launch backend server (uvicorn) in a new console window
# ------------------------------------------------------------
Write-Host "Starting FastAPI backend..."
Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app","--reload" -WorkingDirectory $BackendDir -WindowStyle Normal -PassThru | Out-Null

# ------------------------------------------------------------
# 4️⃣ Frontend setup (npm install)
# ------------------------------------------------------------
$FrontendDir = Join-Target "frontend"
Set-Location $FrontendDir

# Ensure node_modules exists – run npm install if missing
if (-Not (Test-Path "node_modules")) {
    Write-Host "Installing frontend npm packages..."
    npm install
} else {
    Write-Host "npm packages already installed – skipping npm install."
}

# ------------------------------------------------------------
# 5️⃣ Launch Vite dev server in a new console window
# ------------------------------------------------------------
Write-Host "Starting Vite dev server..."
Start-Process -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory $FrontendDir -WindowStyle Normal -PassThru | Out-Null

# ------------------------------------------------------------
# 6️⃣ Simple health‑check after a short wait (backend + proxy)
# ------------------------------------------------------------
Write-Host "Waiting a few seconds for servers to start..."
Start-Sleep -Seconds 8

# Test the backend OTP endpoint (it prints OTP to console)
Write-Host "Checking backend health via OTP request..."
try {
    $response = Invoke-WebRequest -Method POST -Uri "http://127.0.0.1:8000/api/auth/request-otp?mobile=9999999999" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Backend responded: $($response.StatusCode)"
} catch {
    Write-Host "⚠️ Backend health check failed: $_"
}

Write-Host "\n✅ Setup complete.\n   Frontend 👉 http://localhost:5173\n   Backend 👉 http://127.0.0.1:8000\n   You can now use the application."

# Keep the script window open so you can see any messages
Write-Host "Press any key to close this window..."
[void][System.Console]::ReadKey($true)
