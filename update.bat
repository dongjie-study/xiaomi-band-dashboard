@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   小米手环直播间 - 一键更新发布
echo ============================================
echo.

if "%~1"=="" (
    echo 请将当天 Excel 文件拖放到此 bat 图标上运行
    echo.
    echo 当前目录下的 Excel 文件:
    for %%f in (*.xlsx) do echo   %%~nxf
    echo.
    pause
    exit /b 1
)

echo 文件: %~nx1
echo.

echo [1/3] 运行数据分析...
python daily_update.py "%~1"
if %errorlevel% neq 0 (
    echo.
    echo 分析失败！请检查 Excel 文件格式
    pause
    exit /b 1
)

echo.
echo [2/3] 提交更新到 Git...
git add history.json index.html dashboard.html room_comparison.png comparison.png dashboard.png chart.umd.min.js build_html.py generate_dashboard.py daily_update.py update.bat .gitignore
git commit -m "update: %date%"

echo.
echo [3/3] 推送到 GitHub...
git push

echo.
echo ============================================
echo   完成！Cloudflare Pages 将自动部署更新
echo ============================================
pause
