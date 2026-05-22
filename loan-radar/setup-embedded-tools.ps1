$ErrorActionPreference = "Stop"

Write-Output "========================================="
Write-Output "  助贷线索雷达 - 嵌入式工具初始化脚本"
Write-Output "========================================="
Write-Output ""

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsDir = Join-Path $projectDir "electron\resources\tools"
$pythonDir = Join-Path $toolsDir "python"
$pgDir = Join-Path $toolsDir "pgsql"

# --- Python Embedded ---
if (Test-Path (Join-Path $pythonDir "python.exe")) {
    Write-Output "[Python] Already exists, skipping download."
} else {
    Write-Output "[Python] Downloading Python 3.12.9 embeddable package..."
    $pythonZip = Join-Path $toolsDir "python-embed.zip"
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip" -OutFile $pythonZip -UseBasicParsing

    Write-Output "[Python] Extracting..."
    New-Item -ItemType Directory -Force -Path $pythonDir | Out-Null
    Expand-Archive -Path $pythonZip -DestinationPath $pythonDir -Force
    Remove-Item $pythonZip

    Write-Output "[Python] Configuring for pip support..."
    $pthFile = Join-Path $pythonDir "python312._pth"
    Set-Content -Path $pthFile -Value "python312.zip", ".", "Lib", "Lib\site-packages", "", "import site"

    Write-Output "[Python] Installing pip..."
    $getPip = Join-Path $pythonDir "get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
    & (Join-Path $pythonDir "python.exe") $getPip --no-warn-script-location
    Remove-Item $getPip

    Write-Output "[Python] Installing setuptools and wheel..."
    & (Join-Path $pythonDir "python.exe") -m pip install setuptools wheel --no-warn-script-location
}

Write-Output "[Python] Installing backend dependencies..."
& (Join-Path $pythonDir "python.exe") -m pip install -r (Join-Path $projectDir "backend\requirements.txt") --no-warn-script-location

Write-Output "[Python] Installing mediacrawler dependencies..."
& (Join-Path $pythonDir "python.exe") -m pip install -r (Join-Path $projectDir "mediacrawler\requirements.txt") --no-warn-script-location

Write-Output "[Python] Fixing pydantic compatibility..."
& (Join-Path $pythonDir "python.exe") -m pip install "pydantic>=2.7.0" "pydantic-settings>=2.14.0" "fastapi>=0.115.0" "uvicorn[standard]" --no-warn-script-location

Write-Output "[Python] Cleaning cache..."
Get-ChildItem $pythonDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $pythonDir -Recurse -File -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Output "[Python] Done!"
Write-Output ""

# --- PostgreSQL ---
if (Test-Path (Join-Path $pgDir "bin\postgres.exe")) {
    Write-Output "[PostgreSQL] Already exists, skipping copy."
} else {
    $pgSrc = "C:\Program Files\PostgreSQL\16"
    if (-not (Test-Path $pgSrc)) {
        Write-Error "PostgreSQL 16 not found at $pgSrc. Please install PostgreSQL 16 first."
        exit 1
    }

    Write-Output "[PostgreSQL] Copying binaries..."
    New-Item -ItemType Directory -Force -Path $pgDir | Out-Null

    # Copy bin
    New-Item -ItemType Directory -Force -Path "$pgDir\bin" | Out-Null
    Copy-Item "$pgSrc\bin\*.exe" "$pgDir\bin\" -Force
    Copy-Item "$pgSrc\bin\*.dll" "$pgDir\bin\" -Force

    # Copy lib
    Copy-Item "$pgSrc\lib" "$pgDir\lib" -Recurse -Force

    # Copy share
    Copy-Item "$pgSrc\share" "$pgDir\share" -Recurse -Force

    Write-Output "[PostgreSQL] Done!"
}

Write-Output ""
Write-Output "========================================="
Write-Output "  Setup completed!"
Write-Output "========================================="

$pythonSize = (Get-ChildItem $pythonDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
$pgSize = (Get-ChildItem $pgDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Output ("  Python embedded: " + [math]::Round($pythonSize, 1) + " MB")
Write-Output ("  PostgreSQL: " + [math]::Round($pgSize, 1) + " MB")
Write-Output ("  Total: " + [math]::Round($pythonSize + $pgSize, 1) + " MB")
