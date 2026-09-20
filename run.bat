@echo off
title Utility Asset Registry
cd /d "%~dp0"

:menu
cls
echo.
echo  ================================
echo   Utility Asset Registry
echo  ================================
echo.
echo   1 = Start the system
echo   2 = Load survey CSV
echo   3 = Exit
echo.
set /p choice=Type 1, 2 or 3 and press Enter: 

if "%choice%"=="1" goto start
if "%choice%"=="2" goto ingest
if "%choice%"=="3" exit /b 0
goto menu

:start
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo Please run setup.bat one time first.
  pause
  goto menu
)
if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo.
  echo Created .env for you.
  echo Open .env in Notepad and set the admin password,
  echo then choose 1 again.
  pause
  goto menu
)
echo.
echo Starting... Keep this window open.
echo Browser page: http://127.0.0.1:8000/docs
echo.
call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -m uvicorn utility_asset_registry.api.app:create_app --factory --host 127.0.0.1 --port 8000
pause
goto menu

:ingest
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo Please run setup.bat one time first.
  pause
  goto menu
)
if not exist "data\survey_export.csv" (
  echo.
  echo Put the CSV file here first:
  echo   data\survey_export.csv
  pause
  goto menu
)
echo.
echo Loading survey file...
call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -m utility_asset_registry data\survey_export.csv
echo.
echo Finished. See the outputs folder.
pause
goto menu
