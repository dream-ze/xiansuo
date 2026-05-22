@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   助贷线索雷达 - 一键安装
echo ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PG_DIR=%PROJECT_DIR%\tools\pgsql"
set "PG_DATA=%PROJECT_DIR%\data\pgdata"
set "PG_USER=loan_radar"
set "PG_PASSWORD=loan_radar_password"
set "PG_DB=loan_radar"
set "PG_PORT=5432"

echo ============================================
echo   第一步：检查 Python
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python 未安装
    echo   请安装 Python 3.11+ : https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   已安装: %%v
echo   [OK] Python

echo.
echo ============================================
echo   第二步：安装 PostgreSQL（便携版）
echo ============================================
echo.

if exist "%PG_DIR%\bin\psql.exe" (
    for /f "tokens=*" %%v in ('"%PG_DIR%\bin\psql.exe" --version 2^>^&1') do echo   已安装: %%v
    goto :pg_done
)

echo   正在下载 PostgreSQL 便携版...

set "PG_ZIP=%TEMP%\pgsql-portable.zip"

if exist "%PG_ZIP%" (
    echo   发现已下载的安装包，验证中...
    for %%F in ("%PG_ZIP%") do set "PG_ZIP_SIZE=%%~zF"
    if !PG_ZIP_SIZE! LSS 50000000 (
        echo   安装包不完整，重新下载...
        del "%PG_ZIP%" 2>nul
    ) else (
        echo   安装包有效，跳过下载
        goto :pg_extract
    )
)

echo   下载中，请稍候（约 200MB）...
echo   如果下载缓慢，可手动下载后放到 %TEMP%\pgsql-portable.zip

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://sbp.enterprisedb.com/getfile.jsp?fileid=1260202' -OutFile '%PG_ZIP%' -UseBasicParsing" 2>nul

if not exist "%PG_ZIP%" (
    echo   [ERROR] 下载失败
    echo   请手动下载 PostgreSQL 16 便携版:
    echo   https://www.enterprisedb.com/download-postgresql-binaries
    echo   下载后解压到 %PROJECT_DIR%\tools\pgsql
    pause
    exit /b 1
)

for %%F in ("%PG_ZIP%") do set "PG_ZIP_SIZE=%%~zF"
if !PG_ZIP_SIZE! LSS 50000000 (
    echo   [ERROR] 下载的文件不完整（!PG_ZIP_SIZE! 字节）
    echo   请手动下载 PostgreSQL 16 便携版:
    echo   https://www.enterprisedb.com/download-postgresql-binaries
    del "%PG_ZIP%" 2>nul
    pause
    exit /b 1
)

:pg_extract

echo   解压中（可能需要1-2分钟）...
mkdir "%PROJECT_DIR%\tools" 2>nul
powershell -NoProfile -Command "Expand-Archive -Path '%PG_ZIP%' -DestinationPath '%PROJECT_DIR%\tools' -Force" 2>nul

for /d %%d in ("%PROJECT_DIR%\tools\pgsql*") do (
    if /I not "%%~nd"=="pgsql" (
        ren "%%d" pgsql 2>nul
    )
)

if exist "%PG_DIR%\bin\psql.exe" (
    echo   [OK] PostgreSQL 便携版已安装
) else (
    echo   [ERROR] 解压后未找到 psql.exe
    echo   请手动下载 PostgreSQL 16 便携版:
    echo   https://www.enterprisedb.com/download-postgresql-binaries
    echo   下载后解压到 %PROJECT_DIR%\tools\pgsql
    pause
    exit /b 1
)

:pg_done

echo.
echo   初始化数据库...

if exist "%PG_DIR%\bin\psql.exe" (
    set "PSQL_CMD=%PG_DIR%\bin\psql.exe"
    set "PATH=%PG_DIR%\bin;%PATH%"
) else (
    where psql >nul 2>&1
    if not errorlevel 1 (
        set "PSQL_CMD=psql"
    ) else (
        echo   [ERROR] 找不到 psql 命令
        pause
        exit /b 1
    )
)

if not exist "%PG_DATA%\PG_VERSION" (
    if exist "%PG_DIR%\bin\initdb.exe" (
        echo   首次使用，初始化数据目录...
        "%PG_DIR%\bin\initdb.exe" -U postgres -A trust -D "%PG_DATA%" --encoding=UTF8 --locale=C 2>nul
        if errorlevel 1 (
            echo   [ERROR] 数据库初始化失败
            pause
            exit /b 1
        )
        echo   [OK] 数据目录初始化完成
    )
)

if exist "%PG_DIR%\bin\pg_ctl.exe" (
    "%PG_DIR%\bin\pg_ctl.exe" -D "%PG_DATA%" -l "%PROJECT_DIR%\data\pg.log" -o "-p %PG_PORT%" start 2>nul
    if not errorlevel 1 (
        echo   [OK] PostgreSQL 已启动
    ) else (
        echo   [WARN] PostgreSQL 启动失败，可能已在运行
    )
) else (
    echo   [INFO] 尝试启动系统 PostgreSQL 服务...
    net start postgresql-x64-16 >nul 2>&1
    net start postgresql-x64-17 >nul 2>&1
)

timeout /t 3 /nobreak >nul

echo.
echo   创建数据库用户和数据库...

"%PSQL_CMD%" -U postgres -h localhost -p %PG_PORT% -c "SELECT 1;" -t >nul 2>&1
if not errorlevel 1 (
    set "PGCONN=-U postgres -h localhost -p %PG_PORT%"
    goto :pg_create_db
)

"%PSQL_CMD%" "postgresql://postgres:postgres@localhost:%PG_PORT%/postgres" -c "SELECT 1;" >nul 2>&1
if not errorlevel 1 (
    set "PGCONN=postgresql://postgres:postgres@localhost:%PG_PORT%/postgres"
    goto :pg_create_db
)

echo   [ERROR] 无法连接 PostgreSQL
echo   请确认 PostgreSQL 正在运行
pause
exit /b 1

:pg_create_db

"%PSQL_CMD%" %PGCONN% -c "SELECT 1 FROM pg_roles WHERE rolname='%PG_USER%'" 2>nul | findstr "1 row" >nul 2>&1
if errorlevel 1 (
    "%PSQL_CMD%" %PGCONN% -c "CREATE USER %PG_USER% WITH PASSWORD '%PG_PASSWORD%' SUPERUSER;" 2>nul
    echo   [OK] 创建用户 %PG_USER%
) else (
    echo   用户 %PG_USER% 已存在
)

"%PSQL_CMD%" %PGCONN% -lqt 2>nul | findstr "%PG_DB%" >nul 2>&1
if errorlevel 1 (
    "%PSQL_CMD%" %PGCONN% -c "CREATE DATABASE %PG_DB% OWNER %PG_USER%;" 2>nul
    echo   [OK] 创建数据库 %PG_DB%
) else (
    echo   数据库 %PG_DB% 已存在
)

"%PSQL_CMD%" %PGCONN% -c "GRANT ALL PRIVILEGES ON DATABASE %PG_DB% TO %PG_USER%;" 2>nul

echo   [OK] 数据库初始化完成

echo.
echo ============================================
echo   第三步：安装项目依赖
echo ============================================
echo.

echo   [1/3] 安装 Python 依赖...
cd /d "%PROJECT_DIR%\backend"
pip install -r requirements.txt -q 2>nul
if errorlevel 1 (
    echo   重试安装...
    pip install -r requirements.txt 2>nul
)
echo   [OK] Python 依赖

echo   安装 MediaCrawler 内嵌模式...
cd /d "%PROJECT_DIR%"
pip install -e "./mediacrawler" -q 2>nul
if errorlevel 1 (
    echo   [WARN] MediaCrawler 内嵌模式安装失败，采集将使用 HTTP Bridge 模式
) else (
    echo   [OK] MediaCrawler 内嵌模式
)

echo.
echo   [2/3] 构建前端...
cd /d "%PROJECT_DIR%\frontend"

where node >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Node.js 未安装，请安装后重新运行
    echo   https://nodejs.org/
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo   安装前端依赖...
    npm install --registry=https://registry.npmmirror.com 2>nul
    if errorlevel 1 (
        npm install 2>nul
    )
)

echo   构建前端生产版本...
call npm run build 2>nul
if errorlevel 1 (
    echo   [WARN] 前端构建失败，将使用开发模式启动
) else (
    echo   [OK] 前端构建完成
)

echo.
echo   [3/3] 生成配置文件...
cd /d "%PROJECT_DIR%\backend"

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
    ) else (
        (
            echo APP_ENV=production
            echo DATABASE_URL=postgresql+psycopg2://%PG_USER%:%PG_PASSWORD%@localhost:%PG_PORT%/%PG_DB%
            echo SECRET_KEY=dev-only-change-me-in-production-32ch
            echo SCHEDULER_ENABLED=true
            echo SCHEDULER_INTERVAL_SECONDS=60
            echo MEDIA_CRAWLER_HOME=../mediacrawler
            echo MEDIA_CRAWLER_API_URL=http://127.0.0.1:8080
            echo CORS_ORIGINS=http://localhost:8001,http://localhost:5173,http://127.0.0.1:8001
            echo FRONTEND_SERVE_STATIC=true
            echo FRONTEND_BUILD_DIR=../frontend/dist
            echo ASSET_STORAGE_TYPE=local
        ) > .env
    )
    echo   [OK] 生成 .env 配置
) else (
    echo   .env 已存在，跳过
)

echo.
echo   执行数据库迁移...
cd /d "%PROJECT_DIR%\backend"
alembic upgrade head 2>nul
if errorlevel 1 (
    echo   [WARN] 数据库迁移失败，启动时会自动重试
) else (
    echo   [OK] 数据库迁移完成
)

echo.
echo ============================================
echo   安装完成！
echo ============================================
echo.
echo   双击「一键启动.bat」即可启动项目
echo.
pause
exit /b 0
