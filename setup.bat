@echo off
REM One-time setup. Run this once, then use run.bat every day.
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.11 or newer first, then try again.
  pause
  exit /b 1
)

echo Installing... please wait.
python -m venv .venv
call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
".venv\Scripts\python.exe" -m pip install -e ".[dev]"

if not exist ".env" copy /Y ".env.example" ".env" >nul

echo.
echo Done.
echo 1. Open .env in Notepad and set BOOTSTRAP_ADMIN_PASSWORD
echo 2. Double-click run.bat every day
pause
