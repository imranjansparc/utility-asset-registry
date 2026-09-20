@echo off
REM Load the bad sample CSV (most rows should be rejected).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat one time first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -m utility_asset_registry data\sample_incorrect.csv --rejects outputs\rejects_incorrect.csv --map outputs\map_incorrect.geojson --summary outputs\summary_incorrect.txt --log outputs\ingest.log
echo.
echo Open outputs\rejects_incorrect.csv in Excel to see each reason.
pause
