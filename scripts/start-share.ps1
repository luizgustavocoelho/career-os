param([switch]$Install)
& (Join-Path $PSScriptRoot 'start-local.ps1') -Share -Install:$Install
