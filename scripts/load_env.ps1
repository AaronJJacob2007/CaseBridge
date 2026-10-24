# Dot-source from the repository root: . .\scripts\load_env.ps1
$envFile = Join-Path $PSScriptRoot '..\.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    throw 'Missing .env. Copy .env.example to .env and set your local password.'
}
$allowedKeys = @('DATABASE_URL', 'DEMO_TODAY', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB')
foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line.Trim() -eq '' -or $line.TrimStart().StartsWith('#')) { continue }
    $parts = $line.Split('=', 2)
    if ($parts.Count -ne 2 -or $parts[0].Trim() -notin $allowedKeys) {
        throw 'Unexpected .env entry. Use the format in .env.example.'
    }
    [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
}
