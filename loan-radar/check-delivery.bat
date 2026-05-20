@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

set "COMPOSE_CMD=docker compose"

echo ========================================
echo   Loan Radar - Delivery Check
echo ========================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker was not found.
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Docker is not running or cannot be accessed.
    exit /b 1
)
echo [OK] Docker is available.

docker compose version >nul 2>&1
if errorlevel 1 (
    where docker-compose >nul 2>&1
    if errorlevel 1 (
        echo [FAIL] Docker Compose was not found.
        exit /b 1
    )
    set "COMPOSE_CMD=docker-compose"
)
echo [OK] Docker Compose is available.

%COMPOSE_CMD% config --quiet
if errorlevel 1 (
    echo [FAIL] docker-compose.yml is invalid.
    exit /b 1
)
echo [OK] docker-compose.yml is valid.

echo.
echo [Check] Frontend tests...
pushd frontend
call npm.cmd test
if errorlevel 1 (
    popd
    echo [FAIL] Frontend tests failed.
    exit /b 1
)

echo.
echo [Check] Frontend production build...
call npm.cmd run build
if errorlevel 1 (
    popd
    echo [FAIL] Frontend build failed.
    exit /b 1
)
popd
echo [OK] Frontend checks passed.

echo.
echo [Check] Backend Python syntax...
pushd backend
python -m compileall app
if errorlevel 1 (
    popd
    echo [FAIL] Backend syntax check failed.
    exit /b 1
)
popd
echo [OK] Backend syntax check passed.

echo.
echo ========================================
echo   Delivery check completed
echo ========================================
echo.
exit /b 0
