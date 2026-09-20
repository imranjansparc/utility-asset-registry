@echo off
REM Start the web service. Double-click this file, then open the docs page.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup is missing. Ask IT to run setup once.
  echo Expected folder: .venv
  pause
  exit /b 1
)

if not exist ".env" (
  echo Creating .env from .env.example ...
  copy /Y ".env.example" ".env" >nul
  echo.
  echo Open .env and set JWT_SECRET and the admin password, then run this again.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
echo.
echo Service starting...
echo When you see "Uvicorn running", open this in your browser:
echo   http://127.0.0.1:8000/docs
echo.
echo Health check: http://127.0.0.1:8000/health
echo.
echo Keep this window open. Press Ctrl+C to stop.
echo.
".venv\Scripts\python.exe" -m uvicorn utility_asset_registry.api.app:create_app --factory --host 127.0.0.1 --port 8000
pause
