param([ValidateSet('start', 'stop', 'status')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot 'development/apps/web')
try {
    node scripts/dev-background.cjs $Action
    if ($LASTEXITCODE -ne 0) { throw 'FLAME startup failed. See the startup message above.' }
} finally {
    Pop-Location
}
