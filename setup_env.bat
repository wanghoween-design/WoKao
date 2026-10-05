@echo off
REM WoKao-ExamAgent - Windows one-click environment setup (run ONCE)
REM Usage: double-click setup_env.bat (or: setup_env.bat)
REM NOTE: ASCII-only text for Windows GBK cmd.exe compatibility

set "PY=python"
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1 && set "PY=py"
)

echo ==^> Using Python: %PY%
echo ==^> Creating virtualenv .venv
"%PY%" -m venv .venv

echo ==^> Activating virtualenv
call .venv\Scripts\activate.bat

echo ==^> Installing dependencies
pip install -r requirements.txt

echo ==^> Done. Next steps:
echo     1^) edit config.toml and set OPENAI_API_KEY=sk-xxx
echo     2^) run start.bat to launch the server
echo     3^) open http://127.0.0.1:8000 in your browser
pause
