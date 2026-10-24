# Slice 3 plus all Slice 0-2 regression checks. Run from PowerShell.
Set-Location -LiteralPath 'C:\SIH26\CaseBridge'
$ErrorActionPreference = 'Stop'

function Invoke-Check {
    param([string]$Name, [scriptblock]$Action)
    try {
        & $Action
        Write-Output "PASS: $Name"
    } catch {
        Write-Output "FAIL: $Name"
        throw
    }
}

Invoke-Check 'Environment loaded' {
    if (-not (Test-Path .env)) {
        $localPassword = [Guid]::NewGuid().ToString('N')
        (Get-Content .env.example -Raw).Replace('replace_with_local_password', $localPassword) | Set-Content .env
    }
    . .\scripts\load_env.ps1
}
# PASS: Environment loaded (no credentials printed).

Invoke-Check 'Docker Compose available' {
    docker compose version
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose unavailable.' }
}
# PASS: Docker Compose available

Invoke-Check 'Docker engine reachable' {
    docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) { throw 'Open Docker Desktop with Linux containers, then retry.' }
}
# PASS: Docker engine reachable

Invoke-Check 'Compose configuration' {
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Invalid Compose configuration.' }
}
# PASS: Compose configuration

Invoke-Check 'Python environment' {
    if (-not (Test-Path .venv\Scripts\python.exe)) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
}
# PASS: Python environment

Invoke-Check 'Dependencies installed' {
    .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
# PASS: Dependencies installed

Invoke-Check 'Dependency consistency' {
    .\.venv\Scripts\python.exe -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency conflicts.' }
}
# No broken requirements found.
# PASS: Dependency consistency

Invoke-Check 'PostgreSQL healthy' {
    docker compose up -d --wait --wait-timeout 120
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL did not become healthy.' }
    docker compose ps
    if ($LASTEXITCODE -ne 0) { throw 'Container inspection failed.' }
}
# PASS: PostgreSQL healthy (db row also shows healthy).

Invoke-Check 'Six database tables' {
    .\.venv\Scripts\python.exe -m backend.check_db
    if ($LASTEXITCODE -ne 0) { throw 'Table check failed.' }
}
# 6 tables: action_log, case_links, cases, coordination_requests, institutions, users
# PASS: Six database tables

Invoke-Check 'Demo seed loaded' {
    .\.venv\Scripts\python.exe -m backend.seed
    if ($LASTEXITCODE -ne 0) { throw 'Demo seed failed.' }
}
# Seed: 6 users, 8 institutions, 30 cases
# Inserted 30 cases on first run, or 0 on reruns; existing work preserved.
# PASS: Demo seed loaded

Invoke-Check 'Slice 0-3 regression tests' {
    .\.venv\Scripts\python.exe -m pytest backend\tests -q
    if ($LASTEXITCODE -ne 0) { throw 'pytest failed.' }
}
# PASS: pytest reports 118 passed in ...s (duration varies).
# PASS: Slice 0-3 regression tests

Invoke-Check 'Backend port 8000 available' {
    if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
        throw 'Port 8000 is in use. Stop that server yourself, then rerun.'
    }
}
# PASS: Backend port 8000 available

$backendProcess = $null
try {
    Invoke-Check 'Temporary backend started' {
        $script:backendProcess = Start-Process -FilePath "$PWD\.venv\Scripts\python.exe" -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $PWD.Path -WindowStyle Hidden -RedirectStandardOutput "$PWD\backend\verify.stdout.log" -RedirectStandardError "$PWD\backend\verify.stderr.log" -PassThru
    }
    # PASS: Temporary backend started

    Invoke-Check 'Backend ready' {
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
    }
    # PASS: Backend ready

    Invoke-Check 'HTTP acceptance checks' {
        .\.venv\Scripts\python.exe -m backend.verify_http
        if ($LASTEXITCODE -ne 0) { throw 'HTTP acceptance failed.' }
    }
    # Individual HTTP PASS lines followed by PASS: HTTP acceptance checks.


    Invoke-Check 'Slice 2 HTTP acceptance checks' {
        .\.venv\Scripts\python.exe -m backend.verify_http_slice2
        if ($LASTEXITCODE -ne 0) { throw 'Slice 2 HTTP acceptance failed.' }
    }
    # Individual detail/profile/403 audit PASS lines, then PASS: Slice 2 HTTP acceptance checks.


    Invoke-Check 'Slice 3 HTTP acceptance checks' {
        .\.venv\Scripts\python.exe -m backend.verify_http_slice3
        if ($LASTEXITCODE -ne 0) { throw 'Slice 3 HTTP acceptance failed.' }
    }
    # PASS: case reload, denied link review audit, coordination validation; then PASS: Slice 3 HTTP acceptance checks.
} finally {
    if ($null -ne $backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id
    }
    Write-Output 'Verification backend stopped; PostgreSQL left running.'
}
