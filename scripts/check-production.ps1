param([switch]$Live)
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path $pythonExe)) { throw 'Execute scripts/start-local.ps1 -Install primeiro.' }
$arguments = @((Join-Path $PSScriptRoot 'check_production.py'))
if ($Live) { $arguments += '--live' }
& $pythonExe @arguments
if ($LASTEXITCODE) { throw 'Preflight não aprovado. Corrija os itens indicados.' }
