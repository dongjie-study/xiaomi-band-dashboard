@echo off
chcp 65001 >nul
title Traffic data sync
echo ============================================================
echo   Traffic data: ingest -^> verify -^> commit -^> push -^> live check
echo   ^(Chinese messages come from run_daily.py^)
echo ============================================================
set "RUN=%~dp0run_daily.py"
if not exist "%RUN%" (
  for /d %%D in ("%USERPROFILE%\Desktop\*") do (
    if exist "%%~fD\traffic_analysis\run_daily.py" set "RUN=%%~fD\traffic_analysis\run_daily.py"
  )
)
if not exist "%RUN%" (
  echo   [!] run_daily.py not found next to this .bat, nor in any Desktop repo folder.
  echo       Fix: keep this .bat inside the repo's traffic_analysis folder,
  echo            or clone the repo to the Desktop and run it there.
  echo.
  pause
  exit /b 1
)
set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"
%PY% -X utf8 "%RUN%" %*
echo.
pause
