param([switch]$Install, [switch]$Share)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousLocation = Get-Location
$children = @()
$overrides = @{}
function Override-Environment([string]$Name, [string]$Value) {
    $overrides[$Name] = [Environment]::GetEnvironmentVariable($Name, 'Process')
    [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
}
function Stop-OwnedProcess($Process) {
    if ($Process -and -not $Process.HasExited) {
        # Only the process tree created by this invocation.
        & taskkill.exe /PID $Process.Id /T /F 2>$null | Out-Null
    }
}
try {
    Set-Location -LiteralPath $projectRoot
    foreach ($tool in @('python', 'node', 'npm.cmd')) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool não encontrado. Instale Python 3.14 e Node.js 24, reabra o terminal e execute -Install." }
    }
    & python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)'
    if ($LASTEXITCODE) { throw 'É necessário Python 3.14 ou superior.' }
    & node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 24 ? 0 : 1)'
    if ($LASTEXITCODE) { throw 'É necessário Node.js 24 ou superior.' }
    if (Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 3000,8000 }) { throw 'Porta 3000 ou 8000 ocupada. Encerre a instância anterior; nenhum processo existente será encerrado por este script.' }
    if ($Share -and -not (Get-Command cloudflared -ErrorAction SilentlyContinue)) { throw 'Instale cloudflared: winget install --id Cloudflare.cloudflared ; reabra o terminal. Consulte docs/SETUP.md.' }
    $pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if ($Install) {
        if (-not (Test-Path -LiteralPath $pythonExe)) { & python -m venv .venv; if ($LASTEXITCODE) { throw 'Falha ao criar venv.' } }
        & python -m pip --python $pythonExe install -r backend/requirements.lock
        if ($LASTEXITCODE) { throw 'Falha ao instalar dependências Python. Verifique rede e permissões.' }
        Push-Location frontend
        try { & npm.cmd ci; if ($LASTEXITCODE) { throw 'Falha ao instalar dependências Node.' } } finally { Pop-Location }
    }
    if (-not (Test-Path -LiteralPath $pythonExe) -or -not (Test-Path 'frontend/node_modules/next')) { throw 'Dependências ausentes. Execute .\scripts\start-local.ps1 -Install.' }
    & $pythonExe -c 'import fastapi, sqlalchemy, alembic, uvicorn'
    if ($LASTEXITCODE) { throw 'Dependências Python incompletas. Execute -Install.' }
    if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env'; Write-Host '.env criado. Nenhum dado de demonstração será adicionado.' }
    $logDir = Join-Path $projectRoot ('data\logs\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $publicOrigin = 'http://localhost:3000'
    if ($Share) {
        if ((Test-Path "$env:USERPROFILE/.cloudflared/config.yml") -or (Test-Path "$env:USERPROFILE/.cloudflared/config.yaml")) { throw 'Quick Tunnel requer ausência de config.yml/config.yaml em ~/.cloudflared. Consulte a documentação Cloudflare; o script não altera sua configuração.' }
        $tunnelLog = Join-Path $logDir 'tunnel-error.log'
        $tunnel = Start-Process cloudflared -ArgumentList 'tunnel','--url','http://127.0.0.1:3000','--no-autoupdate' -WindowStyle Hidden -PassThru -RedirectStandardError $tunnelLog -RedirectStandardOutput (Join-Path $logDir 'tunnel.log')
        $children += $tunnel
        $deadline = (Get-Date).AddSeconds(60)
        $publicOrigin = $null
        while ((Get-Date) -lt $deadline -and -not $tunnel.HasExited) {
            $text = Get-Content -LiteralPath $tunnelLog -Raw -ErrorAction SilentlyContinue
            if ($text -match 'https://[a-z0-9-]+\.trycloudflare\.com') { $publicOrigin = $Matches[0]; break }
            Start-Sleep -Milliseconds 500
        }
        if (-not $publicOrigin) { throw "Cloudflare não disponibilizou URL. Consulte $tunnelLog" }
        Override-Environment 'APP_ORIGIN' $publicOrigin
        Override-Environment 'ALLOWED_ORIGINS' $publicOrigin
        Override-Environment 'COOKIE_SECURE' 'true'
        Override-Environment 'REGISTRATION_ENABLED' 'false'
        Override-Environment 'NEXT_ALLOWED_DEV_ORIGINS' ([Uri]$publicOrigin).Host
        Write-Host 'Demonstração temporária: mantenha este terminal aberto. Cadastros fechados. Não é deploy de produção.'
    } else {
        Override-Environment 'APP_ORIGIN' $publicOrigin
        Override-Environment 'ALLOWED_ORIGINS' 'http://localhost:3000,http://127.0.0.1:3000'
        Override-Environment 'COOKIE_SECURE' 'false'
        Override-Environment 'NEXT_ALLOWED_DEV_ORIGINS' ''
    }
    Push-Location backend
    try {
        # Consistent SQLite backup before any migration, including WAL contents.
        & $pythonExe -c 'from app.config import settings; from sqlalchemy.engine import make_url; from pathlib import Path; u=make_url(settings().database_url); print("sqlite-existing" if u.get_backend_name()=="sqlite" and u.database and Path(u.database).is_file() else "skip")' | ForEach-Object {
            if ($_ -eq 'sqlite-existing') {
                & $pythonExe -m app.manage backup-sqlite (Join-Path $projectRoot ('data/backups/pre-start-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.db'))
                if ($LASTEXITCODE) { throw 'Backup falhou; migration não será executada.' }
            }
        }
        & $pythonExe -m alembic upgrade head
        if ($LASTEXITCODE) { throw 'Falha nas migrations. Preserve o backup e consulte os logs.' }
    } finally { Pop-Location }
    foreach ($service in @('api','worker')) {
        $arguments = if ($service -eq 'api') { @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') } else { @('-m','app.worker') }
        $process = Start-Process $pythonExe -ArgumentList $arguments -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir "$service.log") -RedirectStandardError (Join-Path $logDir "$service-error.log")
        $children += $process
    }
    $apiReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try { $null = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; $apiReady = $true; break } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $apiReady) { throw "API não iniciou. Logs: $logDir" }
    $frontend = Start-Process (Get-Command node).Source -ArgumentList 'node_modules/next/dist/bin/next','dev','--hostname','127.0.0.1' -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'frontend.log') -RedirectStandardError (Join-Path $logDir 'frontend-error.log')
    $children += $frontend
    Write-Host "CareerOS: $publicOrigin"
    Write-Host "Ctrl+C encerra os serviços e o túnel desta execução. Logs: $logDir"
    while ($true) {
        foreach ($process in $children) { if ($process.HasExited) { throw "Um serviço encerrou inesperadamente. Logs: $logDir" } }
        Start-Sleep -Seconds 1
    }
} finally {
    [array]::Reverse($children)
    foreach ($process in $children) { Stop-OwnedProcess $process }
    foreach ($key in $overrides.Keys) { [Environment]::SetEnvironmentVariable($key, $overrides[$key], 'Process') }
    Set-Location -LiteralPath $previousLocation.Path
}
