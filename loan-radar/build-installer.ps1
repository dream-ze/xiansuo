$ErrorActionPreference = 'Stop'

Write-Output '========================================='
Write-Output '  Build Installer'
Write-Output '========================================='
Write-Output ''

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$electronDir = Join-Path $projectDir 'electron'

$env:ELECTRON_MIRROR = 'https://npmmirror.com/mirrors/electron/'
$env:ELECTRON_BUILDER_BINARIES_MIRROR = 'https://npmmirror.com/mirrors/electron-builder-binaries/'

Write-Output '[1/4] Compiling TypeScript...'
Set-Location $electronDir
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Error 'TypeScript compilation failed!'
    exit 1
}
Write-Output '  OK'
Write-Output ''

Write-Output '[2/4] Checking resources...'
$toolsDir = Join-Path $electronDir 'resources\tools'
$pythonDir = Join-Path $toolsDir 'python'
$pgDir = Join-Path $toolsDir 'pgsql'

if (-not (Test-Path (Join-Path $pythonDir 'python.exe'))) {
    Write-Error 'Embedded Python not found'
    exit 1
}
if (-not (Test-Path (Join-Path $pgDir 'bin\postgres.exe'))) {
    Write-Error 'PostgreSQL not found'
    exit 1
}
$iconPath = Join-Path $electronDir 'assets\icon.ico'
if (-not (Test-Path $iconPath)) {
    Write-Error 'Icon not found'
    exit 1
}
Write-Output '  Python: OK'
Write-Output '  PostgreSQL: OK'
Write-Output '  Icon: OK'
Write-Output ''

Write-Output '[3/4] Checking frontend build...'
$frontendDist = Join-Path $projectDir 'frontend\dist\index.html'
if (-not (Test-Path $frontendDist)) {
    Write-Error 'Frontend not built'
    exit 1
}
Write-Output '  OK'
Write-Output ''

Write-Output '[4/4] Building NSIS installer...'
npm run dist
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Build failed!'
    exit 1
}

Write-Output ''
Write-Output '========================================='
Write-Output '  Build completed!'
Write-Output '========================================='

$releaseDir = Join-Path $projectDir 'release'
if (Test-Path $releaseDir) {
    Write-Output ''
    Write-Output 'Output files:'
    Get-ChildItem $releaseDir -File | ForEach-Object {
        $sizeMB = [math]::Round($_.Length / 1MB, 1)
        $msg = $_.Name + ' (' + $sizeMB + ' MB)'
        Write-Output $msg
    }
}

Write-Output ''
Write-Output $releaseDir