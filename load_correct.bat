@echo off
REM Load the clean sample CSV (all rows should be accepted).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat one time first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -m utility_asset_registry data\sample_correct.csv --rejects outputs\rejects_correct.csv --map outputs\map_correct.geojson --summary outputs\summary_correct.txt --log outputs\ingest.log
echo.
echo Expected: all rows accepted, rejects empty or header only.
pause
