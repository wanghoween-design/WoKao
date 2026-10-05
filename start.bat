@echo off
REM WoKao-ExamAgent - Windows one-click start script
REM ASCII-only on purpose for GBK cmd.exe compatibility

cd /d %~dp0

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment .venv not found!
    echo [HINT] Please run setup_env.bat first to initialize the environment.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

REM Build the frontend on first run (dist/ is not committed to the repo)
if not exist "frontend\dist\index.html" (
    echo [INFO] Frontend build not found. Building frontend/ ...
    where npm >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] npm not found in PATH. Install Node.js 18+ and re-run, or
        echo        build manually: cd frontend ^&^& npm install ^&^& npm run build
        pause
        exit /b 1
    )
    pushd frontend
    call npm install
    call npm run build
    popd
    if not exist "frontend\dist\index.html" (
        echo [ERROR] Frontend build failed. See npm output above.
        pause
        exit /b 1
    )
)

echo =======================================================
echo    WoKao-ExamAgent - AI Exam Planner Academy
echo =======================================================
echo [INFO] Starting FastAPI server at http://127.0.0.1:8000
echo [INFO] Press Ctrl+C in this window to stop the server.
echo =======================================================

REM Open the browser once the server has had a moment to boot
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000"

python -m uvicorn server:app --host 127.0.0.1 --port 8000
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start server.
    echo [HINT] If port 8000 is in use, run: netstat -ano ^| findstr :8000
    echo        Then kill the PID with: taskkill /PID ^<PID^> /F
)
pause
