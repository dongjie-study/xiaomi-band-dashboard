@echo off
chcp 65001 >nul
title Traffic data sync
echo ============================================================
echo   Traffic data: ingest -^> verify -^> commit -^> push
echo   ^(Chinese messages come from run_daily.py^)
echo ============================================================
python -X utf8 "%USERPROFILE%\Desktop\小米手环直播间销量分析\traffic_analysis\run_daily.py" %*
echo.
pause
