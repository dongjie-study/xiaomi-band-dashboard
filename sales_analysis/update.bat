@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   小米手环直播间 - 一键更新发布
echo ============================================
echo.

if "%~1"=="" (
    echo 用法 1（推荐）: 先选竞对Excel，按住Ctrl再选我方Excel
    echo          → 两个文件一起拖到此bat图标上
    echo.
    echo 用法 2: 只拖一个合并好的Excel（需含type列）
    echo.
    echo 当前目录的 Excel 文件：
    for %%f in (*.xlsx) do echo   %%~nxf
    echo.
    pause
    exit /b 1
)

echo 竞对数据: %~nx1
if "%~2"=="" (
    echo 我方数据: (未提供，按单文件合并模式处理)
) else (
    echo 我方数据: %~nx2
)
echo.

echo [1/3] 运行数据分析...
if "%~2"=="" (
    python daily_update.py "%~1"
) else (
    python daily_update.py "%~1" "%~2"
)

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
echo   完成！网站已自动更新
echo   https://xiaomi-band-dashboard.pages.dev
echo ============================================
pause
