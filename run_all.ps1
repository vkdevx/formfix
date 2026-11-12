# Run both backend (FastAPI) and frontend (Vite) with minimal setup.
# Usage: powershell -ExecutionPolicy Bypass -File .\run_all.ps1

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# ---------- Backend ----------
$BackendDir = Join-Path $Root "backend"
Push-Location $BackendDir

# Create virtualenv if missing
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
# Activate venv
& "$BackendDir\.venv\Scripts\Activate.ps1"

# Install deps if needed
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
} elseif (Test-Path "pyproject.toml") {
    pip install poetry
    poetry install
}

# Start FastAPI in a new window
Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app","--reload" -WorkingDirectory $BackendDir

Pop-Location

# ---------- Frontend ----------
$FrontendDir = Join-Path $Root "frontend"
Push-Location $FrontendDir

# Install npm packages if node_modules missing
if (-not (Test-Path "node_modules")) {
    npm install
}

# Start Vite dev server in a new window
Start-Process -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory $FrontendDir

Pop-Location

Write-Host "`n🚀 Both backend and frontend are running."
Write-Host "   Backend:  http://127.0.0.1:8000"
Write-Host "   Frontend: http://localhost:5173`n"
