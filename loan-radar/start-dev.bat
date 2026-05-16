@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   助贷线索雷达 - 本地开发启动脚本
echo ============================================
echo.

echo [1/4] 检查环境...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 未安装
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js 未安装
    pause
    exit /b 1
)

echo.
echo [2/4] 设置 MediaCrawler 内嵌模式...
set MEDIA_CRAWLER_HOME=%~dp0mediacrawler
echo   MEDIA_CRAWLER_HOME=%MEDIA_CRAWLER_HOME%

echo.
echo [3/4] 启动后端服务 (端口 8001)...
start "Loan Radar Backend" cmd /k "set MEDIA_CRAWLER_HOME=%~dp0mediacrawler && cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"

echo.
echo [4/4] 启动前端开发服务器 (端口 5173)...
start "Loan Radar Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   本地开发环境已启动！
echo ============================================
echo.
echo   前端界面:  http://localhost:5173
echo   后端 API:  http://localhost:8001/docs
echo.
echo   MediaCrawler 已配置为内嵌模式，无需单独启动。
echo   如需使用 HTTP Bridge 模式，请另开终端启动：
echo   cd %~dp0mediacrawler
echo   uv run uvicorn api.main:app --port 8080 --reload
echo.
pause
