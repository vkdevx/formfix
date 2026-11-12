@echo off
setlocal

REM ==== Backend ==== 
pushd "%~dp0backend"
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

start "Backend" cmd /k "uvicorn app.main:app --reload"
popd

REM ==== Frontend ==== 
pushd "%~dp0frontend"
if not exist "node_modules" (
    npm install
)

start "Frontend" cmd /k "npm run dev"
popd

echo.
echo All services started.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173
pause
