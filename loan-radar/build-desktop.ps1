$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"
$env:ELECTRON_BUILDER_BINARIES_MIRROR = "https://npmmirror.com/mirrors/electron-builder-binaries/"

$ProjectDir = "d:\Project\智获客雷达\loan-radar"
$ElectronDir = "$ProjectDir\electron"
$ToolsDir = "$ElectronDir\resources\tools"

Write-Host "============================================"
Write-Host "  Loan Radar - Build Desktop App"
Write-Host "============================================"
Write-Host ""

# [1/6] Build frontend
Write-Host "[1/6] Building frontend ..."
Set-Location "$ProjectDir\frontend"
if (-not (Test-Path "node_modules")) {
    npm install --registry=https://registry.npmmirror.com 2>$null
    if ($LASTEXITCODE -ne 0) { npm install 2>$null }
}
npm run build 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "  [ERROR] Frontend build failed"; exit 1 }
Write-Host "  [OK] Frontend build done"
Write-Host ""

# [2/6] Download Python embeddable
Write-Host "[2/6] Preparing Python embeddable ..."
$PythonZip = "$env:TEMP\python-3.11.9-embed-amd64.zip"
$PythonDir = "$ToolsDir\python"

if (-not (Test-Path $PythonDir)) {
    if (-not (Test-Path $PythonZip)) {
        Write-Host "  Downloading Python 3.11.9 embeddable ..."
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -OutFile $PythonZip -UseBasicParsing
    }
    New-Item -ItemType Directory -Path $PythonDir -Force | Out-Null
    Write-Host "  Extracting Python ..."
    Expand-Archive -Path $PythonZip -DestinationPath $PythonDir -Force

    $pthFile = Get-ChildItem "$PythonDir\*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName -Raw
        $content = $content -replace '#import site', 'import site'
        Set-Content $pthFile.FullName $content
    }

    Write-Host "  Installing pip ..."
    $GetPip = "$env:TEMP\get-pip.py"
    if (-not (Test-Path $GetPip)) {
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip -UseBasicParsing
    }
    & "$PythonDir\python.exe" $GetPip 2>&1 | Out-Null

    Write-Host "  Installing backend dependencies ..."
    & "$PythonDir\python.exe" -m pip install -r "$ProjectDir\backend\requirements.txt" -q 2>&1 | Out-Null

    Write-Host "  Installing mediacrawler dependencies ..."
    & "$PythonDir\python.exe" -m pip install -r "$ProjectDir\mediacrawler\requirements.txt" -q 2>&1 | Out-Null

    Write-Host "  Installing shared packages ..."
    & "$PythonDir\python.exe" -m pip install -e "$ProjectDir\mediacrawler" -q 2>&1 | Out-Null
}
Write-Host "  [OK] Python embeddable ready"
Write-Host ""

# [3/6] Download PostgreSQL portable
Write-Host "[3/6] Preparing PostgreSQL portable ..."
$PgZip = "$env:TEMP\pgsql-portable.zip"
$PgDir = "$ToolsDir\pgsql"

if (-not (Test-Path $PgDir)) {
    if (-not (Test-Path $PgZip)) {
        Write-Host "  Downloading PostgreSQL 16 portable (~310MB) ..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260202" -OutFile $PgZip -UseBasicParsing
    }
    New-Item -ItemType Directory -Path "$ToolsDir" -Force | Out-Null
    Write-Host "  Extracting PostgreSQL (this may take a minute) ..."
    Expand-Archive -Path $PgZip -DestinationPath $ToolsDir -Force
    Get-ChildItem "$ToolsDir\pgsql*" -Directory | Where-Object { $_.Name -ne "pgsql" } | ForEach-Object {
        Rename-Item $_.FullName "pgsql" -ErrorAction SilentlyContinue
    }
}
Write-Host "  [OK] PostgreSQL portable ready"
Write-Host ""

# [3.5/6] Download ffmpeg
Write-Host "[3.5/6] Preparing ffmpeg ..."
$FfmpegDir = "$ToolsDir\ffmpeg"

if (-not (Test-Path "$FfmpegDir\ffmpeg.exe")) {
    $FfmpegZip = "$env:TEMP\ffmpeg-release-essentials.zip"
    if (-not (Test-Path $FfmpegZip)) {
        Write-Host "  Downloading ffmpeg essentials build ..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $FfmpegZip -UseBasicParsing
    }
    Write-Host "  Extracting ffmpeg ..."
    $tempExtract = "$env:TEMP\ffmpeg-extract"
    if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
    Expand-Archive -Path $FfmpegZip -DestinationPath $tempExtract -Force
    New-Item -ItemType Directory -Path $FfmpegDir -Force | Out-Null
    $binDir = Get-ChildItem "$tempExtract\*essentials*\bin" -Directory | Select-Object -First 1
    if ($binDir) {
        Copy-Item "$($binDir.FullName)\ffmpeg.exe" "$FfmpegDir\" -Force
        Copy-Item "$($binDir.FullName)\ffprobe.exe" "$FfmpegDir\" -Force
    }
    Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
}
if (Test-Path "$FfmpegDir\ffmpeg.exe") {
    Write-Host "  [OK] ffmpeg ready"
} else {
    Write-Host "  [WARN] ffmpeg not found - video cover extraction will not work"
}
Write-Host ""

# [4/6] Install Electron dependencies
Write-Host "[4/6] Installing Electron dependencies ..."
Set-Location $ElectronDir
if (-not (Test-Path "node_modules")) {
    npm install --registry=https://registry.npmmirror.com 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "  [WARN] npm install had issues" }
}
Write-Host "  [OK] Electron dependencies"
Write-Host ""

# [5/6] Build Electron app
Write-Host "[5/6] Building Electron app ..."
Set-Location $ElectronDir
npm run build 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "  [WARN] TypeScript build had issues" }
Write-Host "  [OK] Electron app built"
Write-Host ""

# [6/6] Verify tools
Write-Host "[6/6] Verifying build artifacts ..."
$hasPython = Test-Path "$PythonDir\python.exe"
$hasPgsql = Test-Path "$PgDir\bin\pg_ctl.exe"
$hasFrontend = Test-Path "$ProjectDir\frontend\dist\index.html"
$hasElectron = Test-Path "$ElectronDir\dist\main.js"

if ($hasPython) { Write-Host "  [OK] Python embeddable" } else { Write-Host "  [WARN] Python embeddable NOT found at $PythonDir" }
if ($hasPgsql) { Write-Host "  [OK] PostgreSQL portable" } else { Write-Host "  [WARN] PostgreSQL portable NOT found at $PgDir" }
if ($hasFrontend) { Write-Host "  [OK] Frontend build" } else { Write-Host "  [WARN] Frontend build NOT found" }
if ($hasElectron) { Write-Host "  [OK] Electron build" } else { Write-Host "  [WARN] Electron build NOT found" }
Write-Host ""

Write-Host "============================================"
Write-Host "  Build complete!"
Write-Host "============================================"
Write-Host ""
Write-Host "  To test:  cd electron && npm run start"
Write-Host "  To pack:  cd electron && npm run dist"
Write-Host ""
