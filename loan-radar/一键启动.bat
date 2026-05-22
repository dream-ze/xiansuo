@echo off
setlocal enabledelayedexpansion

set "APP_NAME=助贷线索雷达"
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PG_DIR=%PROJECT_DIR%\tools\pgsql"
set "PG_DATA=%PROJECT_DIR%\data\pgdata"
set "PG_PORT=5432"

echo ============================================
echo   %APP_NAME% - 一键启动
echo ============================================
echo.

echo [1/3] 环境检查 ...

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装，请先运行 setup.bat
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%\backend\.env" (
    echo [ERROR] 配置文件不存在，请先运行 setup.bat
    pause
    exit /b 1
)

echo   [OK] Python 和配置文件

echo.
echo [2/3] 启动 PostgreSQL ...

set "PG_STARTED=0"

netstat -an 2>nul | findstr "LISTENING" | findstr ":%PG_PORT% " >nul 2>&1
if not errorlevel 1 (
    echo   [OK] PostgreSQL 已在运行
    set "PG_STARTED=1"
)

if "%PG_STARTED%"=="0" (
    if exist "%PG_DIR%\bin\pg_ctl.exe" (
        if not exist "%PG_DATA%\PG_VERSION" (
            echo   首次使用，初始化数据目录...
            "%PG_DIR%\bin\initdb.exe" -U postgres -A trust -D "%PG_DATA%" --encoding=UTF8 --locale=C 2>nul
        )
        "%PG_DIR%\bin\pg_ctl.exe" -D "%PG_DATA%" -l "%PROJECT_DIR%\data\pg.log" -o "-p %PG_PORT%" start 2>nul
        if not errorlevel 1 (
            echo   [OK] PostgreSQL 便携版已启动
            set "PG_STARTED=1"
        )
    )
)

if "%PG_STARTED%"=="0" (
    echo   尝试启动系统 PostgreSQL 服务...
    net start postgresql-x64-16 >nul 2>&1
    net start postgresql-x64-17 >nul 2>&1
    timeout /t 2 /nobreak >nul
    netstat -an 2>nul | findstr "LISTENING" | findstr ":%PG_PORT% " >nul 2>&1
    if not errorlevel 1 (
        echo   [OK] PostgreSQL 系统服务已启动
        set "PG_STARTED=1"
    )
)

if "%PG_STARTED%"=="0" (
    echo   [WARN] PostgreSQL 未启动，后端可能无法连接数据库
)

echo.
echo [3/3] 启动后端服务 ...

set "MEDIA_CRAWLER_HOME=%PROJECT_DIR%\mediacrawler"
set "FRONTEND_SERVE_STATIC=true"
set "FRONTEND_BUILD_DIR=..\frontend\dist"

cd /d "%PROJECT_DIR%\backend"

if exist "%PROJECT_DIR%\frontend\dist\index.html" (
    echo   模式: 生产模式（后端直接提供前端页面）
) else (
    echo   模式: 开发模式
    echo   [WARN] 前端未构建，请先运行 setup.bat
)

echo.
echo   启动中，请稍候...
echo   访问地址: http://localhost:8001
echo   API 文档:  http://localhost:8001/docs
echo.
echo   按 Ctrl+C 停止服务
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
