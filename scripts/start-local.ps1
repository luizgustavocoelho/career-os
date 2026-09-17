param([switch]$Install)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if ($Install) {
    if (-not (Test-Path -LiteralPath $pythonExe)) { python -m venv .venv; if ($LASTEXITCODE) { throw 'Falha ao criar ambiente Python.' } }
    python -m pip --python $pythonExe install -r backend/requirements.lock
    if ($LASTEXITCODE) { throw 'Falha ao instalar dependências Python.' }
    Push-Location frontend
    try { npm ci; if ($LASTEXITCODE) { throw 'Falha ao instalar dependências Node.' } } finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Execute primeiro .\scripts\start-local.ps1 -Install' }
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
if ((Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 3000,8000 })) { throw 'As portas 3000 ou 8000 já estão em uso. Encerre a instância anterior antes de iniciar outra.' }
Push-Location backend
try { & $pythonExe -m alembic upgrade head; if ($LASTEXITCODE) { throw 'Falha nas migrations.' } } finally { Pop-Location }
$logDir = Join-Path $projectRoot 'data\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$apiProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'api.log') -RedirectStandardError (Join-Path $logDir 'api-error.log')
$workerProcess = Start-Process -FilePath $pythonExe -ArgumentList '-m','app.worker' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'worker.log') -RedirectStandardError (Join-Path $logDir 'worker-error.log')
Write-Host 'CareerOS: http://localhost:3000'
Write-Host 'Pressione Ctrl+C para encerrar. Logs da API e worker: data/logs.'
try {
    Push-Location frontend
    try { npm run dev } finally { Pop-Location }
} finally {
    if (-not $apiProcess.HasExited) { $apiProcess.Kill() }
    if (-not $workerProcess.HasExited) { $workerProcess.Kill() }
}
