# WIN OS across Linux, macOS and Windows (2026-11-10)

## The architecture decision that makes this simple
WIN OS ships as Linux containers. On every operator OS the stack itself is
identical; only the *workstation tooling* differs:

| Layer | Linux | macOS | Windows |
|---|---|---|---|
| Stack runtime | Docker Engine + compose plugin | Docker Desktop (or Colima) | Docker Desktop with **WSL2 backend** (required) |
| CPU images | amd64/arm64 | Apple Silicon arm64 + Intel amd64 - all stack images publish both | amd64 (arm64 via WSL2 also fine) |
| Preflight | preflight.sh (runs on the Ubuntu target too) | preflight.sh on the target; workstation: same checks by hand or in terminal | **preflight.ps1** (workstation checks) + preflight.sh still runs on the Ubuntu target |
| Deployment verify | verify-deployment.sh | verify-deployment.sh | **verify-deployment.ps1** (same six checks) |
| Backup / restore | backup-win-os.sh | backup-win-os.sh | Run inside WSL2 or from the postgres container (pg_dump speaks the same everywhere) |
| Ansible control node | native | pipx install ansible | **WSL2 only** - Ansible does not support a Windows control node; targets are unaffected |
| Make targets | native | native (Xcode CLT) | WSL2 / Git Bash, or call `docker compose --env-file .env -f win-os/compose.yaml ...` directly (the Makefile is a thin wrapper) |
| Python tooling | python3 | python3 | `py -3` wherever docs say python3 |

## Rules that keep checkouts safe on every OS
- `win-os/.gitattributes` pins LF for shell scripts, Python, YAML and the
  Dockerfile, and CRLF for .ps1 - a Windows clone can no longer corrupt the
  scripts that run inside Linux containers.
- No host networking, no docker.sock mounts, named volumes only: the
  compose files are Docker-Desktop-safe as shipped.
- No POSIX-only calls in the Python code (audited 2026-11-10); paths go
  through environment variables and pathlib-style joins.

## Verification, not assertion
- `win-os-xplat-ci` (copy-ready at win-os/ci/win-os-xplat-ci.yml) runs the
  full API test suite on Ubuntu, Windows and macOS GitHub runners on every
  push to win-os/** - cross-OS regressions fail loudly.
- The deploy-verify workflow proves the container stack on Ubuntu;
  Docker Desktop uses the same Linux VM model on macOS and Windows, so a
  green Ubuntu run plus green per-OS test matrices is the compatibility
  evidence. A physical Windows/Mac install is still the final smoke test
  for a given operator machine.
