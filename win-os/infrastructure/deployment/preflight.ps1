# WIN OS preflight - Windows operator workstation edition.
# The DEPLOYMENT TARGET is Ubuntu Server (see preflight.sh, which runs
# there). This script checks the Windows workstation you drive the
# deployment from: Docker Desktop, the compose plugin, and a filled .env.
# Usage: powershell -ExecutionPolicy Bypass -File preflight.ps1
$ErrorActionPreference = "Stop"
function Fail($msg) { Write-Error "PREFLIGHT FAIL: $msg"; exit 1 }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "docker is not available; install Docker Desktop with the WSL2 backend"
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fail "docker compose plugin is not available" }
Write-Host "Docker Desktop + compose plugin - OK"

if (-not (Test-Path ".env")) { Fail ".env is missing; copy win-os/.env.example to .env and fill in real values" }
if (Select-String -Path ".env" -Pattern "change-me" -Quiet) { Fail ".env still contains placeholder secrets" }
Write-Host ".env present, no placeholder secrets - OK"

$drive = Get-PSDrive -Name ((Get-Location).Drive.Name)
if ($drive.Free -lt 10GB) { Fail "less than 10 GB free disk" }
Write-Host "Disk space - OK"
Write-Host "PREFLIGHT OK (workstation). Server-side preflight.sh still runs on the Ubuntu host."
