Set-Location -LiteralPath 'C:\SIH26\CaseBridge'
# PASS: working directory is C:\SIH26\CaseBridge.
$ErrorActionPreference = 'Stop'

if (-not (Test-Path .env)) {
    $localPassword = [Guid]::NewGuid().ToString('N')
    (Get-Content .env.example -Raw).Replace('replace_with_local_password', $localPassword) | Set-Content .env
}
. .\scripts\load_env.ps1
Write-Output 'PASS: .env loaded (credentials hidden)'
# PASS: PASS: .env loaded (credentials hidden)

docker compose version
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose unavailable.' }
# PASS: Docker Compose version v... (version varies).

docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Open Docker Desktop with Linux containers, then retry.' }
# PASS: Docker server version; no connection or permission error.

docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Invalid Compose configuration.' }
# PASS: no output, successful exit.

if (-not (Test-Path .venv\Scripts\python.exe)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
# PASS: .venv\Scripts\python.exe exists; creation normally prints nothing.

.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
# PASS: installed/already satisfied messages; successful exit.

.\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency conflicts.' }
# PASS: No broken requirements found.

docker compose up -d --wait --wait-timeout 120
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL did not become healthy.' }
# PASS: db container becomes Healthy; successful exit.

docker compose ps
if ($LASTEXITCODE -ne 0) { throw 'Container inspection failed.' }
# PASS: db row shows Up ... (healthy), 127.0.0.1:5432->5432/tcp.

.\.venv\Scripts\python.exe -m backend.check_db
if ($LASTEXITCODE -ne 0) { throw 'Table check failed.' }
# PASS: 6 tables: action_log, case_links, cases, coordination_requests, institutions, users

.\.venv\Scripts\python.exe -m pytest backend\tests -q
if ($LASTEXITCODE -ne 0) { throw 'pytest failed.' }
# PASS: 2 passed in ...s (duration varies).

if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8000 is in use. Stop that server yourself, then rerun.'
}
$backendProcess = Start-Process -FilePath "$PWD\.venv\Scripts\python.exe" -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $PWD.Path -WindowStyle Hidden -RedirectStandardOutput "$PWD\backend\verify.stdout.log" -RedirectStandardError "$PWD\backend\verify.stderr.log" -PassThru
# PASS: temporary backend starts on port 8000; logs go to backend/verify.*.log.
try {
    $healthy = $false
    $lastHealthError = 'No successful response.'
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($backendProcess.HasExited) {
            Get-Content backend\verify.stderr.log
            throw 'Backend exited before health check.'
        }
        try {
            $response = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2
            if ($response.status -eq 'ok' -and $response.database -eq 'ok') {
                $healthy = $true
                break
            }
            $lastHealthError = 'Unexpected health response.'
        } catch {
            $lastHealthError = $_.Exception.Message
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $healthy) { throw "Health check failed: $lastHealthError" }
    Write-Output 'PASS: HTTP 200 /health {"status":"ok","database":"ok"}'
    # PASS: PASS: HTTP 200 /health {"status":"ok","database":"ok"}
} finally {
    if (-not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id }
    Write-Output 'Verification backend stopped; PostgreSQL left running.'
    # PASS: Verification backend stopped; PostgreSQL left running.
}
