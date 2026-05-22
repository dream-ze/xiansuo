@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   助贷线索雷达 - 打包发布
echo ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "DIST_DIR=%PROJECT_DIR%\dist"
set "PKG_NAME=loan-radar"

for /f "usebackq" %%t in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd-HHmm'"`) do set "TIMESTAMP=%%t"

echo [1/5] 构建前端生产版本 ...

cd /d "%PROJECT_DIR%\frontend"
if not exist "node_modules" (
    echo   安装前端依赖...
    npm install --registry=https://registry.npmmirror.com 2>nul
    if errorlevel 1 (
        npm install 2>nul
    )
)

call npm run build 2>nul
if errorlevel 1 (
    echo   [ERROR] 前端构建失败
    pause
    exit /b 1
)
echo   [OK] 前端构建完成

echo.
echo [2/5] 收集文件 ...
if exist "%DIST_DIR%" rd /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%\%PKG_NAME%"

echo   复制项目文件 ...

robocopy "%PROJECT_DIR%\apis" "%DIST_DIR%\%PKG_NAME%\apis" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1
robocopy "%PROJECT_DIR%\backend" "%DIST_DIR%\%PKG_NAME%\backend" /E /XD __pycache__ .venv venv node_modules .pytest_cache .browser_state .superpowers storage reports /XF *.pyc .env *.log /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1
robocopy "%PROJECT_DIR%\frontend\dist" "%DIST_DIR%\%PKG_NAME%\frontend\dist" /E /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1
robocopy "%PROJECT_DIR%\mediacrawler" "%DIST_DIR%\%PKG_NAME%\mediacrawler" /E /XD __pycache__ .venv .git .pytest_cache node_modules browser_data data test tests docs .github /XF *.pyc .env uv.lock .pre-commit-config.yaml .python-version mypy.ini /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1
robocopy "%PROJECT_DIR%\docs" "%DIST_DIR%\%PKG_NAME%\docs" /E /XD archive /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1

copy "%PROJECT_DIR%\docker-compose.yml" "%DIST_DIR%\%PKG_NAME%\" >nul 2>&1
copy "%PROJECT_DIR%\.gitignore" "%DIST_DIR%\%PKG_NAME%\" >nul 2>&1
copy "%PROJECT_DIR%\setup.bat" "%DIST_DIR%\%PKG_NAME%\" >nul 2>&1
copy "%PROJECT_DIR%\一键启动.bat" "%DIST_DIR%\%PKG_NAME%\" >nul 2>&1
copy "%PROJECT_DIR%\restart_pg.bat" "%DIST_DIR%\%PKG_NAME%\" >nul 2>&1
copy "%PROJECT_DIR%\check-delivery.bat" "%DIST_DIR%\%PKG_NAME%\" >nul 2>&1
copy "%PROJECT_DIR%\DELIVERY_README.txt" "%DIST_DIR%\%PKG_NAME%\" >nul 2>&1
copy "%PROJECT_DIR%\DELIVERY_CHECKLIST.md" "%DIST_DIR%\%PKG_NAME%\" >nul 2>&1

robocopy "%PROJECT_DIR%\xhs_utils" "%DIST_DIR%\%PKG_NAME%\xhs_utils" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1
robocopy "%PROJECT_DIR%\static" "%DIST_DIR%\%PKG_NAME%\static" /E /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1
robocopy "%PROJECT_DIR%\scripts" "%DIST_DIR%\%PKG_NAME%\scripts" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS >nul 2>&1

echo   [OK] 项目文件已收集

echo.
echo [3/5] 创建 ZIP 压缩包 ...

set "ZIP_FILE=%PROJECT_DIR%\%PKG_NAME%-%TIMESTAMP%.zip"

where 7z >nul 2>&1
if not errorlevel 1 (
    7z a -tzip -mx=5 "%ZIP_FILE%" "%DIST_DIR%\%PKG_NAME%" >nul 2>&1
) else (
    powershell -NoProfile -Command "Compress-Archive -Path '%DIST_DIR%\%PKG_NAME%' -DestinationPath '%ZIP_FILE%' -CompressionLevel Optimal -Force" 2>nul
)

if exist "%ZIP_FILE%" (
    for %%F in ("%ZIP_FILE%") do echo   [OK] %%~nxF
    powershell -NoProfile -Command "$s=(Get-Item '%ZIP_FILE%').Length; Write-Host ('   大小: {0:N1} MB' -f ($s/1MB))" 2>nul
) else (
    echo   [ERROR] ZIP 创建失败
)

echo.
echo [4/5] 创建自解压安装包 ...

set "SFX_FILE=%PROJECT_DIR%\%PKG_NAME%-%TIMESTAMP%-setup.exe"

where 7z >nul 2>&1
if not errorlevel 1 (
    echo   使用 7-Zip 创建自解压包 ...

    set "SFX_MODULE="
    if exist "C:\Program Files\7-Zip\7z.sfx" set "SFX_MODULE=C:\Program Files\7-Zip\7z.sfx"
    if exist "C:\Program Files (x86)\7-Zip\7z.sfx" set "SFX_MODULE=C:\Program Files (x86)\7-Zip\7z.sfx"

    if defined SFX_MODULE (
        echo ;!@Install@!UTF-8!> "%DIST_DIR%\config.txt"
        echo Title=助贷线索雷达 安装>> "%DIST_DIR%\config.txt"
        echo BeginPrompt=确定要安装助贷线索雷达吗？>> "%DIST_DIR%\config.txt"
        echo ExtractDialogText=正在解压安装文件，请稍候...>> "%DIST_DIR%\config.txt"
        echo ExtractPathText=安装路径:>> "%DIST_DIR%\config.txt"
        echo RunProgram="setup.bat">> "%DIST_DIR%\config.txt"
        echo ;!@InstallEnd@!>> "%DIST_DIR%\config.txt"

        copy /b "!SFX_MODULE!" + "%DIST_DIR%\config.txt" + "%ZIP_FILE%" "%SFX_FILE%" >nul 2>&1
        if exist "%SFX_FILE%" (
            echo   [OK] 自解压安装包已创建
            powershell -NoProfile -Command "$s=(Get-Item '%SFX_FILE%').Length; Write-Host ('   大小: {0:N1} MB' -f ($s/1MB))" 2>nul
        ) else (
            echo   [WARN] 自解压包创建失败
        )
    ) else (
        echo   [SKIP] 未找到 7z.sfx 模块
        echo   安装 7-Zip 完整版可获得此功能: https://7-zip.org/
    )
) else (
    echo   [SKIP] 未找到 7-Zip，跳过自解压包
    echo   安装 7-Zip 可获得此功能: https://7-zip.org/
)

echo.
echo [5/5] 清理临时文件 ...
rd /s /q "%DIST_DIR%" 2>nul

echo.
echo ============================================
echo   打包完成
echo ============================================
echo.

if exist "%ZIP_FILE%" (
    powershell -NoProfile -Command "$s=(Get-Item '%ZIP_FILE%').Length; Write-Host ('  ZIP: %PKG_NAME%-%TIMESTAMP%.zip  ({0:N1} MB)' -f ($s/1MB))"
) else (
    echo   ZIP:  失败
)

if exist "%SFX_FILE%" (
    powershell -NoProfile -Command "$s=(Get-Item '%SFX_FILE%').Length; Write-Host ('  EXE: %PKG_NAME%-%TIMESTAMP%-setup.exe  ({0:N1} MB)' -f ($s/1MB))"
) else (
    echo   EXE:  未生成（需要 7-Zip）
)

echo.
echo   输出目录: %PROJECT_DIR%\
echo.
echo   部署步骤:
echo     1. 解压 ZIP 或运行 EXE
echo     2. 运行 setup.bat 安装依赖
echo     3. 运行 一键启动.bat 启动项目
echo.
pause
