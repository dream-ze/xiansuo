@echo off
chcp 65001 >nul 2>&1
setlocal

set "PROJECT_ROOT=%~dp0loan-radar"

if not exist "%PROJECT_ROOT%\start.bat" (
    echo [ERROR] Cannot find launcher:
    echo %PROJECT_ROOT%\start.bat
    echo.
    pause
    exit /b 1
)

call "%PROJECT_ROOT%\start.bat"
