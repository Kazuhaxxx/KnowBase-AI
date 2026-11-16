# KnowBase AI - 1-Click Independent Local and Public Launcher

$Host.UI.RawUI.WindowTitle = "KnowBase AI - Launcher"
Clear-Host

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   KnowBase AI - Starting Services                          " -ForegroundColor Cyan
Write-Host "   Your Knowledge. One Intelligent Assistant.               " -ForegroundColor DarkCyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootPath = (Get-Item $ScriptDir).Parent.FullName
Set-Location $RootPath

# 1. Start Ollama (CPU Mode to prevent GPU memory crashes)
Write-Host "[1/4] Checking Ollama..." -ForegroundColor Yellow
$ollamaRunning = $false
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    $ollamaRunning = $true
} catch {
    $ollamaRunning = $false
}

if (-not $ollamaRunning) {
    Write-Host "      Starting Ollama daemon in CPU mode..." -ForegroundColor Gray
    $env:CUDA_VISIBLE_DEVICES = "-1"
    $ollamaExe = "C:\Users\User\AppData\Local\Programs\Ollama\ollama.exe"
    if (Test-Path $ollamaExe) {
        Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    } else {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    }
    Start-Sleep -Seconds 3
}
Write-Host "      [OK] Ollama is online on http://127.0.0.1:11434" -ForegroundColor Green

# 2. Start FastAPI Backend
Write-Host "[2/4] Starting KnowBase Backend API..." -ForegroundColor Yellow
$pyPath = Join-Path $RootPath "backend\.venv\Scripts\python.exe"
$backendCmd = "`$env:PYTHONPATH='backend'; & '$pyPath' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
$backendProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -WindowStyle Minimized -PassThru

# Wait for backend health check
$backendReady = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
        if ($h.status -eq "ok") {
            $backendReady = $true
            break
        }
    } catch {}
}
if ($backendReady) {
    Write-Host "      [OK] Backend API is online on http://127.0.0.1:8000" -ForegroundColor Green
} else {
    Write-Host "      [INFO] Backend is still loading, continuing..." -ForegroundColor DarkYellow
}

# 3. Start Next.js Frontend
Write-Host "[3/4] Starting Next.js Frontend..." -ForegroundColor Yellow
$frontendCmd = "cd '$RootPath\frontend'; npm run dev"
$frontendProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Minimized -PassThru

# Wait for frontend port 3000
$frontendReady = $false
for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($res.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch {}
}
if ($frontendReady) {
    Write-Host "      [OK] Frontend is online on http://localhost:3000" -ForegroundColor Green
} else {
    Write-Host "      [INFO] Frontend is compiling modules, continuing..." -ForegroundColor DarkYellow
}

# 4. Start Cloudflare Public Tunnel
Write-Host "[4/4] Generating Secure Public URL via Cloudflare Tunnel..." -ForegroundColor Yellow
$cloudflaredExe = Join-Path $RootPath "cloudflared.exe"
$tunnelLog = Join-Path $RootPath "cloudflared_tunnel.log"
if (Test-Path $tunnelLog) { 
    Remove-Item $tunnelLog -Force -ErrorAction SilentlyContinue 
}

$tunnelProc = Start-Process -FilePath $cloudflaredExe -ArgumentList "tunnel", "--url", "http://localhost:3000", "--logfile", "`"$tunnelLog`"" -WindowStyle Hidden -PassThru

$publicUrl = $null
for ($i = 0; $i -lt 25; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $tunnelLog) {
        $content = Get-Content $tunnelLog -Raw -ErrorAction SilentlyContinue
        if ($content -match "https://[a-zA-Z0-9\-_]+\.trycloudflare\.com") {
            $publicUrl = $matches[0]
            break
        }
    }
}

Clear-Host
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   KnowBase AI is LIVE and READY!                           " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host " LOCAL ACCESS:" -ForegroundColor White
Write-Host "    Frontend:   http://localhost:3000" -ForegroundColor Cyan
Write-Host "    API Docs:   http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""

if ($publicUrl) {
    Write-Host " PUBLIC INTERNET LINK (Accessible from any phone or laptop):" -ForegroundColor White
    Write-Host "    $publicUrl" -ForegroundColor Yellow -BackgroundColor DarkBlue
    Write-Host ""
    try {
        Set-Clipboard -Value $publicUrl
        Write-Host "    (The link has been copied to your clipboard!)" -ForegroundColor DarkGray
    } catch {}
    Write-Host ""
    Start-Process $publicUrl
} else {
    Write-Host " PUBLIC INTERNET LINK:" -ForegroundColor White
    Write-Host "    Check cloudflared_tunnel.log for the generated URL." -ForegroundColor Yellow
    Start-Process "http://localhost:3000"
}

Write-Host " DEMO ACCOUNTS:" -ForegroundColor White
Write-Host "    Employee:   employee@novatech-demo.internal  /  EmployeeDemo!2026" -ForegroundColor Gray
Write-Host "    Admin:      admin@novatech-demo.internal     /  AdminDemo!2026" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Keep this window open while using KnowBase AI." -ForegroundColor Gray
Write-Host " To stop all services, run stop_demo.bat or close this window." -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Green

$pidFile = Join-Path $RootPath ".running_pids.json"
@{
    BackendPid = $backendProc.Id
    FrontendPid = $frontendProc.Id
    TunnelPid = $tunnelProc.Id
} | ConvertTo-Json | Set-Content $pidFile -Force

while ($true) {
    Start-Sleep -Seconds 10
}
