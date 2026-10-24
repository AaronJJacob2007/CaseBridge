# Run AFTER scripts/verify.ps1 passes. Does not install packages or start Docker.
Set-Location -LiteralPath 'C:\SIH26\CaseBridge'
$ErrorActionPreference = 'Stop'
. .\scripts\load_env.ps1
if (-not (Test-Path .venv\Scripts\python.exe) -or -not (Test-Path frontend\node_modules\vite\bin\vite.js)) {
    throw 'Run scripts/verify.ps1 first to prepare dependencies and the database.'
}
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Stop that server yourself before starting this session."
    }
}
$backendProcess = $null
$frontendProcess = $null
try {
    $backendProcess = Start-Process -FilePath "$PWD\.venv\Scripts\python.exe" -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $PWD.Path -WindowStyle Hidden -RedirectStandardOutput "$PWD\backend\dev.stdout.log" -RedirectStandardError "$PWD\backend\dev.stderr.log" -PassThru
    $frontendProcess = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList "$PWD\frontend\node_modules\vite\bin\vite.js",'--host','127.0.0.1','--port','5173','--strictPort' -WorkingDirectory "$PWD\frontend" -WindowStyle Hidden -RedirectStandardOutput "$PWD\frontend\dev.stdout.log" -RedirectStandardError "$PWD\frontend\dev.stderr.log" -PassThru
    $ready = $false
    $lastStartupError = 'No successful response.'
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if ($backendProcess.HasExited -or $frontendProcess.HasExited) {
            Get-Content backend\dev.stderr.log,frontend\dev.stderr.log
            throw 'A development server exited during startup.'
        }
        try {
            $response = Invoke-RestMethod 'http://127.0.0.1:5173/api/health' -TimeoutSec 2
            if ($response.status -eq 'ok' -and $response.database -eq 'ok') { $ready = $true; break }
            $lastStartupError = 'Unexpected health response.'
        } catch { $lastStartupError = $_.Exception.Message }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "Development startup failed: $lastStartupError" }
    Write-Output 'Frontend: http://127.0.0.1:5173'
    Write-Output 'Backend: http://127.0.0.1:8000'
    Write-Output 'Keep this window open. Press Ctrl+C to stop both servers.'
    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
    if ($backendProcess.HasExited) { Get-Content backend\dev.stderr.log }
    if ($frontendProcess.HasExited) { Get-Content frontend\dev.stderr.log }
    throw 'A development server exited. Inspect its log output above.'
} finally {
    if ($null -ne $frontendProcess -and -not $frontendProcess.HasExited) { Stop-Process -Id $frontendProcess.Id }
    if ($null -ne $backendProcess -and -not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id }
    Write-Output 'Development servers stopped; PostgreSQL left running.'
}
