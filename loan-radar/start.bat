@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   助贷线索雷达 - 一键启动脚本
echo ============================================
echo.

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker 未安装，请先安装 Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

where docker-compose >nul 2>&1 || docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose 未安装
    pause
    exit /b 1
)

echo [1/4] 构建 Docker 镜像...
docker compose build

if %errorlevel% neq 0 (
    echo [ERROR] Docker 镜像构建失败
    pause
    exit /b 1
)

echo.
echo [2/4] 启动所有服务...
docker compose up -d

if %errorlevel% neq 0 (
    echo [ERROR] 服务启动失败
    pause
    exit /b 1
)

echo.
echo [3/4] 等待服务就绪...
timeout /t 15 /nobreak >nul

echo.
echo [4/4] 检查服务状态...
docker compose ps

echo.
echo ============================================
echo   启动完成！
echo ============================================
echo.
echo   前端界面:  http://localhost
echo   后端 API:  http://localhost:8001/docs
echo   MediaCrawler: http://localhost:8080/docs
echo   PostgreSQL:  localhost:5432
echo.
echo   查看日志:  docker compose logs -f
echo   停止服务:  docker compose down
echo   重启服务:  docker compose restart
echo.
pause
