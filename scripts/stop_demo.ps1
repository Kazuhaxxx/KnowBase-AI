# KnowBase AI - Stop Independent Local Services

Write-Host "Stopping KnowBase AI services..." -ForegroundColor Yellow

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootPath = (Get-Item $ScriptDir).Parent.FullName
$pidFile = Join-Path $RootPath ".running_pids.json"

if (Test-Path $pidFile) {
    try {
        $pids = Get-Content $pidFile -Raw | ConvertFrom-Json
        if ($pids.BackendPid) { Stop-Process -Id $pids.BackendPid -Force -ErrorAction SilentlyContinue }
        if ($pids.FrontendPid) { Stop-Process -Id $pids.FrontendPid -Force -ErrorAction SilentlyContinue }
        if ($pids.TunnelPid) { Stop-Process -Id $pids.TunnelPid -Force -ErrorAction SilentlyContinue }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    } catch {}
}

$ports = @(8000, 3000)
foreach ($p in $ports) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            if ($c.OwningProcess -gt 0) {
                Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {}
}

Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "[OK] All KnowBase AI background services have been stopped." -ForegroundColor Green
Start-Sleep -Seconds 2
