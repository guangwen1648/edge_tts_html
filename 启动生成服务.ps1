# Edge TTS 生成服务 - PowerShell 启动脚本（自诊断 + 自动探测 Python）
# 即使 PATH 里没有 python 也能跑（自动探测 E:\python3_13_12 等常见位置）

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Show-Banner {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Edge TTS Generation Service" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Working dir: $ScriptDir" -ForegroundColor Gray
    Write-Host "Port: 8765" -ForegroundColor Yellow
    Write-Host "Health: http://127.0.0.1:8765/health" -ForegroundColor Yellow
    Write-Host ""
}

Show-Banner

# === 核心：自动探测 Python 真实路径 ===
$PYTHON = $null
$candidates = @(
    "python",                        # 先试 PATH
    "E:\python3_13_12\python.exe",   # 用户机器实测位置
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe",
    "C:\Python310\python.exe",
    "C:\Program Files\Python313\python.exe",
    "C:\Program Files\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\python.exe"
)

foreach ($cand in $candidates) {
    if ($cand -eq "python") {
        # 试 PATH
        $v = & python --version 2>&1
    } else {
        if (-not (Test-Path $cand)) { continue }
        $v = & $cand --version 2>&1
    }
    if ($LASTEXITCODE -eq 0) {
        $PYTHON = if ($cand -eq "python") { "python" } else { $cand }
        Write-Host "[OK] Python found: $PYTHON  ($v)" -ForegroundColor Green
        break
    }
}

if (-not $PYTHON) {
    Write-Host "[FAIL] Could not find Python. Tried:" -ForegroundColor Red
    foreach ($c in $candidates) { Write-Host "  - $c" -ForegroundColor Yellow }
    Write-Host "Install Python 3.10+ or add it to PATH" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# === 2. 验证 edge_tts 模块 ===
$check = & $PYTHON -c "import edge_tts; print('edge_tts OK')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] edge-tts not installed" -ForegroundColor Red
    Write-Host "  Run: $PYTHON -m pip install edge-tts" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] $check" -ForegroundColor Green

# === 3. 检查端口占用（自动 kill 旧进程） ===
$portInUse = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" }
if ($portInUse) {
    Write-Host "[WARN] Port 8765 in use by PID $($portInUse.OwningProcess), killing..." -ForegroundColor Yellow
    $portInUse | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
    # 二次确认
    $stillInUse = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" }
    if ($stillInUse) {
        Write-Host "[FAIL] Port 8765 still in use, abort" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[OK] Killed and freed" -ForegroundColor Green
}

# === 4. 启动服务 ===
Write-Host ""
Write-Host "[START] Launching edge-tts-serve.py ..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& $PYTHON edge-tts-serve.py 8765
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[CRASH] Service exited with code $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
