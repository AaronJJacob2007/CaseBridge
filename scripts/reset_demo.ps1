# Explicitly destructive demo operation. Never invoked by verify.ps1 or the UI.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    . .\scripts\load_env.ps1
    foreach ($port in @(8000, 5173)) {
        if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
            throw "Stop the development servers with Ctrl+C before resetting (port $port is in use)."
        }
    }
    Write-Output 'Resetting the local synthetic demo: all case actions, links and coordination requests will be replaced by the original seed.'
    .\.venv\Scripts\python.exe -m backend.reset_demo
    if ($LASTEXITCODE -ne 0) { throw 'Demo reset failed; the database transaction was rolled back.' }
} finally { Pop-Location }
