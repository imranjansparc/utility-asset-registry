@echo off
REM Load today's survey CSV. Double-click this file — no Python knowledge needed.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup is missing. Ask IT to run setup once.
  echo Expected folder: .venv
  pause
  exit /b 1
)

if not exist "data\survey_export.csv" (
  echo Put the day's CSV here first:
  echo   %cd%\data\survey_export.csv
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -m utility_asset_registry data\survey_export.csv
echo.
echo Done. Check the Rejects file and Summary under the outputs folder.
pause
