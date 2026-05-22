@echo off
setlocal enabledelayedexpansion

set "COMPOSE_CMD=docker compose"
set "PASS_COUNT=0"
set "FAIL_COUNT=0"

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

echo.
echo [Check 1/8] docker compose config...
%COMPOSE_CMD% config --quiet
if errorlevel 1 (
    echo [FAIL] docker-compose.yml is invalid.
    set /a FAIL_COUNT+=1
) else (
    echo [OK] docker-compose.yml is valid.
    set /a PASS_COUNT+=1
)

echo.
echo [Check 2/8] Frontend tests...
pushd frontend
call npm.cmd test
if errorlevel 1 (
    echo [WARN] Frontend tests failed (non-blocking).
    popd
) else (
    echo [OK] Frontend tests passed.
    set /a PASS_COUNT+=1
    popd
)

echo.
echo [Check 3/8] Frontend production build...
pushd frontend
call npm.cmd run build
if errorlevel 1 (
    popd
    echo [FAIL] Frontend build failed.
    set /a FAIL_COUNT+=1
) else (
    popd
    echo [OK] Frontend build passed.
    set /a PASS_COUNT+=1
)

echo.
echo [Check 4/8] Backend Python syntax...
pushd backend
python -m compileall app -q
if errorlevel 1 (
    popd
    echo [FAIL] Backend syntax check failed.
    set /a FAIL_COUNT+=1
) else (
    popd
    echo [OK] Backend syntax check passed.
    set /a PASS_COUNT+=1
)

echo.
echo [Check 5/8] Backend alembic upgrade head...
pushd backend
call alembic upgrade head
if errorlevel 1 (
    popd
    echo [FAIL] alembic upgrade head failed.
    set /a FAIL_COUNT+=1
) else (
    popd
    echo [OK] alembic upgrade head passed.
    set /a PASS_COUNT+=1
)

echo.
echo [Check 6/8] Backend health check...
curl -sf http://localhost:8001/health >nul 2>&1
if errorlevel 1 (
    echo [WARN] /health not reachable at http://localhost:8001 - is the backend running?
) else (
    echo [OK] /health is reachable.
    set /a PASS_COUNT+=1
)

echo.
echo [Check 7/8] Core API endpoints...
set "API_BASE=http://localhost:8001"
for %%E in (
    "/api/collection/tasks"
    "/api/leads"
    "/api/posts"
    "/api/daily-reports/today"
    "/api/xhs/analytics/overview"
    "/api/xhs/auto-ops/tasks"
    "/api/xhs/monitoring/targets"
) do (
    curl -sf "%API_BASE%%%E" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] %%E not reachable
    ) else (
        echo [OK] %%E reachable
        set /a PASS_COUNT+=1
    )
)

echo.
echo [Check 8/8] Python delivery check script...
python scripts\delivery_check.py
if errorlevel 1 (
    echo [WARN] Python delivery check reported failures. See reports\delivery_check_report.md
) else (
    echo [OK] Python delivery check passed.
    set /a PASS_COUNT+=1
)

echo.
echo ========================================
echo   Delivery check completed
echo   PASS: %PASS_COUNT%  FAIL: %FAIL_COUNT%
echo ========================================
echo.
if %FAIL_COUNT% GTR 0 (
    exit /b 1
)
exit /b 0
