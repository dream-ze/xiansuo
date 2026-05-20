@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

set "APP_NAME=Loan Radar"
set "APP_URL=http://localhost"
set "API_URL=http://localhost:8001/health"
set "CRAWLER_URL=http://localhost:8080/api/health"
set "COMPOSE_CMD=docker compose"
set "COMPOSE_UP_ARGS=up -d"

if /I "%~1"=="--build" (
    set "COMPOSE_UP_ARGS=up -d --build"
)

echo ========================================
echo   %APP_NAME% - Windows Launcher
echo ========================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker was not found.
    echo Install Docker Desktop first:
    echo https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is installed but not running.
    echo Start Docker Desktop, wait until it is ready, then run this file again.
    echo.
    pause
    exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
    where docker-compose >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker Compose was not found.
        echo Update Docker Desktop or install Docker Compose.
        echo.
        pause
        exit /b 1
    )
    set "COMPOSE_CMD=docker-compose"
)

cd /d "%~dp0"

echo [1/4] Starting services...
%COMPOSE_CMD% %COMPOSE_UP_ARGS%
if errorlevel 1 (
    echo.
    echo [ERROR] Service startup failed.
    echo Run "%COMPOSE_CMD% logs --tail=120" for details.
    echo If this is the first run, check your internet connection or Docker registry mirror.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/4] Waiting for backend API...
call :wait_for_url "%API_URL%" 90
if errorlevel 1 (
    echo.
    echo [WARN] Backend health check did not pass in time: %API_URL%
    echo The service may still be starting. Check logs if the page does not load.
)

echo.
echo [3/4] Waiting for MediaCrawler API...
call :wait_for_url "%CRAWLER_URL%" 120
if errorlevel 1 (
    echo.
    echo [WARN] MediaCrawler health check did not pass in time: %CRAWLER_URL%
    echo Some collection features may be unavailable until it is healthy.
)

echo.
echo [4/4] Opening Web UI...
start "" "%APP_URL%"

echo.
echo ========================================
echo   %APP_NAME% is starting
echo ========================================
echo.
echo Web UI:       %APP_URL%
echo Backend API:  http://localhost:8001/docs
echo MediaCrawler: http://localhost:8080/docs
echo PostgreSQL:   localhost:5432
echo.
echo Useful commands:
echo   %COMPOSE_CMD% ps
echo   %COMPOSE_CMD% logs -f
echo   %COMPOSE_CMD% down
echo   %COMPOSE_CMD% restart
echo   start.bat --build
echo.
pause
exit /b 0

:wait_for_url
set "TARGET_URL=%~1"
set "WAIT_SECONDS=%~2"
set /a "ELAPSED=0"

:wait_loop
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%TARGET_URL%' -TimeoutSec 3; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [OK] %TARGET_URL%
    exit /b 0
)

if %ELAPSED% geq %WAIT_SECONDS% (
    exit /b 1
)

set /a "ELAPSED+=3"
timeout /t 3 /nobreak >nul
goto wait_loop
