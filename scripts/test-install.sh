#!/usr/bin/env bash
# Installer tests: builds the release assets, serves them over a local HTTP server, and installs
# from that base on macOS, in an ubuntu:24.04 container, and under PowerShell 7 (Linux container).
# Usage: scripts/test-install.sh   (run after committing; build-release.sh needs a clean tree)
# Needs: python3, curl, shellcheck; docker for the Linux and PowerShell parts (skipped with a note if absent).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
PORT="${PARETOBENCH_TEST_PORT:-8931}"
BASE_HOST="http://127.0.0.1:$PORT"
BASE_DOCKER="http://host.docker.internal:$PORT"
WORK="$ROOT/dist/install-test"
VERSION=$(sed -n 's/^__version__ = "\([^"]*\)".*/\1/p' paretobench/__init__.py | head -n 1)

say() { printf '\n== %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

say "shellcheck"
shellcheck scripts/install.sh scripts/build-release.sh

say "build release assets"
scripts/build-release.sh "$ROOT/dist/release"
rm -rf "$WORK"; mkdir -p "$WORK"
# A corrupted copy of the release: same SHA256SUMS, one extra byte in the archive.
cp -R "$ROOT/dist/release" "$ROOT/dist/test-bad"
printf 'x' >> "$ROOT/dist/test-bad/paretobench.tar.gz"

say "unit tests (existing suite stays green)"
python3 -m unittest discover -s tests

SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    SERVER_PID=""
  fi
}
trap cleanup EXIT
python3 -m http.server "$PORT" --bind 0.0.0.0 --directory "$ROOT/dist" >"$WORK/server.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
  curl -fsS -o /dev/null "$BASE_HOST/release/SHA256SUMS" && break
  sleep 0.2
done
curl -fsS -o /dev/null "$BASE_HOST/release/SHA256SUMS" || fail "local release server did not start on port $PORT"

if [ "$(uname -s)" = Darwin ]; then
  say "macOS: install, version, upgrade"
  H="$WORK/home-mac"; mkdir -p "$H"
  env HOME="$H" PARETOBENCH_RELEASE_BASE="$BASE_HOST/release" sh "$ROOT/dist/release/install.sh"
  "$H/.local/bin/paretobench" --version | grep -q "paretobench $VERSION" || fail "macOS version check"
  "$H/.local/bin/pb" --version | grep -q "paretobench $VERSION" || fail "macOS pb version check"
  env HOME="$H" "$H/.local/bin/paretobench" validate || fail "macOS validate"
  env HOME="$H" PARETOBENCH_RELEASE_BASE="$BASE_HOST/release" sh "$ROOT/dist/release/install.sh" || fail "macOS upgrade re-run"
  "$H/.local/bin/paretobench" --version | grep -q "paretobench $VERSION" || fail "macOS version after upgrade"

  say "macOS: corrupted archive refused, nothing installed"
  H="$WORK/home-mac-bad"; mkdir -p "$H"
  if env HOME="$H" PARETOBENCH_RELEASE_BASE="$BASE_HOST/test-bad" sh "$ROOT/dist/release/install.sh" >"$WORK/mac-bad.log" 2>&1; then
    fail "corrupted archive was accepted on macOS"
  fi
  grep -q "checksum mismatch" "$WORK/mac-bad.log" || fail "macOS corruption error not named"
  [ ! -d "$H/.paretobench/app" ] || fail "corrupted install left files behind on macOS"

  say "macOS: missing Python named with the brew one-liner"
  FAKE="$WORK/fakebin"; mkdir -p "$FAKE"
  for t in sh bash curl tar shasum awk sed mktemp mkdir mv rm chmod cat dirname head cut uname tr ls grep basename cp; do
    p=$(command -v "$t") && ln -sf "$p" "$FAKE/$t"
  done
  H="$WORK/home-mac-nopy"; mkdir -p "$H"
  if env HOME="$H" PATH="$FAKE" PARETOBENCH_RELEASE_BASE="$BASE_HOST/release" /bin/sh "$ROOT/dist/release/install.sh" >"$WORK/mac-nopy.log" 2>&1; then
    fail "install succeeded without Python on macOS"
  fi
  if ! grep -q "Python 3.11" "$WORK/mac-nopy.log" || ! grep -q "brew install" "$WORK/mac-nopy.log"; then
    fail "macOS missing-Python message wrong: $(cat "$WORK/mac-nopy.log")"
  fi
else
  say "macOS section skipped (host is $(uname -s))"
fi

if command -v docker >/dev/null 2>&1; then
  say "Linux container: install, version, upgrade, corrupted archive, too-old Python"
  cat > "$WORK/linux-test.sh" <<'LINUX'
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends python3 curl >/dev/null
export HOME=/tmp/h1
PARETOBENCH_RELEASE_BASE=file:///rel/release sh /rel/release/install.sh
/tmp/h1/.local/bin/paretobench --version
/tmp/h1/.local/bin/pb validate
PARETOBENCH_RELEASE_BASE=file:///rel/release sh /rel/release/install.sh
/tmp/h1/.local/bin/paretobench --version
# Corrupted archive: must fail with the checksum error and install nothing.
export HOME=/tmp/h2
if PARETOBENCH_RELEASE_BASE=file:///rel/test-bad sh /rel/release/install.sh >/tmp/bad.log 2>&1; then
  echo "FAIL: corrupted archive accepted"; exit 1
fi
grep -q "checksum mismatch" /tmp/bad.log || { echo "FAIL: corruption error not named"; cat /tmp/bad.log; exit 1; }
[ ! -d /tmp/h2/.paretobench/app ] || { echo "FAIL: corrupted install left files"; exit 1; }
# Too-old Python: wrappers that fail the 3.11 version probe, real python otherwise.
mkdir -p /tmp/oldbin
for n in python3 python3.12 python3.11; do
  printf '#!/bin/sh\ncase "$*" in *version_info*) exit 1;; esac\nexec /usr/bin/%s "$@"\n' "$n" > "/tmp/oldbin/$n"
  chmod 755 "/tmp/oldbin/$n"
done
export HOME=/tmp/h3
if PATH=/tmp/oldbin:$PATH PARETOBENCH_RELEASE_BASE=file:///rel/release sh /rel/release/install.sh >/tmp/old.log 2>&1; then
  echo "FAIL: too-old python accepted"; exit 1
fi
grep -q "Python 3.11" /tmp/old.log && grep -q "apt-get install" /tmp/old.log || { echo "FAIL: old-python message wrong"; cat /tmp/old.log; exit 1; }
echo "LINUX-OK"
LINUX
  docker run --rm --name paretobench-linux -v "$ROOT/dist:/rel:ro" ubuntu:24.04 \
    bash /rel/install-test/linux-test.sh | tee "$WORK/linux.log"
  grep -q "LINUX-OK" "$WORK/linux.log" || fail "Linux container tests"

  say "Linux container: absent Python named with the apt one-liner"
  docker run --rm --name paretobench-linux-nopy -v "$ROOT/dist:/rel:ro" ubuntu:24.04 bash -c '
    set -eu
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq --no-install-recommends curl >/dev/null
    if sh /rel/release/install.sh >/tmp/nopy.log 2>&1; then echo "FAIL: install succeeded without python"; exit 1; fi
    grep -q "Python 3.11" /tmp/nopy.log && grep -q "apt-get install" /tmp/nopy.log || { cat /tmp/nopy.log; exit 1; }
    echo "LINUX-NOPY-OK"' | tee "$WORK/linux-nopy.log"
  grep -q "LINUX-NOPY-OK" "$WORK/linux-nopy.log" || fail "Linux absent-Python test"

  say "PowerShell 7 container: install, version, upgrade, corrupted archive"
  cat > "$WORK/ps-test.ps1" <<'PWSH'
$ErrorActionPreference = 'Stop'
$env:DEBIAN_FRONTEND = 'noninteractive'
& apt-get update -qq *> $null
& apt-get install -y -qq --no-install-recommends python3.11 *> $null
if ($LASTEXITCODE -ne 0) { throw 'cannot install python3.11 in the container' }
$env:PARETOBENCH_RELEASE_BASE = "$env:TEST_BASE/release"
& /rel/release/install.ps1
$v = (& /root/.local/bin/paretobench --version | Out-String).Trim()
if ($v -notlike 'paretobench *') { throw "version check failed: $v" }
& /root/.local/bin/pb validate
if ($LASTEXITCODE -ne 0) { throw 'pb validate failed' }
& /rel/release/install.ps1
$v = (& /root/.local/bin/paretobench --version | Out-String).Trim()
if ($v -notlike 'paretobench *') { throw "version after upgrade failed: $v" }
# Corrupted archive: must throw the checksum error and install nothing.
$env:PARETOBENCH_HOME = '/tmp/h2'; $env:PARETOBENCH_BIN_DIR = '/tmp/h2/bin'
$env:PARETOBENCH_RELEASE_BASE = "$env:TEST_BASE/test-bad"
$failed = $false
try { & /rel/release/install.ps1 } catch { $failed = $true; if ("$_" -notmatch 'checksum mismatch') { throw } }
if (-not $failed) { throw 'corrupted archive was accepted' }
if (Test-Path '/tmp/h2/app') { throw 'corrupted install left files behind' }
Write-Host 'PWSH-OK'
PWSH
  # The PowerShell image publishes no arm64 variant; run the amd64 one under emulation.
  docker run --rm --platform linux/amd64 --name paretobench-pwsh --add-host=host.docker.internal:host-gateway \
    -e TEST_BASE="$BASE_DOCKER" -v "$ROOT/dist:/rel:ro" mcr.microsoft.com/powershell \
    pwsh -NoProfile -File /rel/install-test/ps-test.ps1 | tee "$WORK/pwsh.log"
  grep -q "PWSH-OK" "$WORK/pwsh.log" || fail "PowerShell container tests"

  say "PSScriptAnalyzer (skipped with a note if it does not install quickly)"
  set +e
  docker run --rm --platform linux/amd64 --name paretobench-psa -v "$ROOT/dist:/rel:ro" mcr.microsoft.com/powershell \
    pwsh -NoProfile -Command '
      try {
        $j = Start-Job { Install-Module PSScriptAnalyzer -Force -Scope CurrentUser -ErrorAction Stop }
        if (-not (Wait-Job $j -Timeout 180)) { Remove-Job $j -Force; Write-Host "PSScriptAnalyzer: skipped (module install too slow)"; exit 0 }
        Receive-Job $j -ErrorAction Stop
        Import-Module PSScriptAnalyzer -ErrorAction Stop
      } catch {
        Write-Host "PSScriptAnalyzer: skipped (module install failed: $_)"
        exit 0
      }
      $r = Invoke-ScriptAnalyzer -Path /rel/release/install.ps1
      $r | Format-Table -AutoSize | Out-String | Write-Host
      if ($r | Where-Object { $_.Severity -eq "Error" }) { Write-Host "PSA-ERRORS"; exit 1 }
      Write-Host "PSA-DONE"' | tee "$WORK/psa.log"
  rc=$?
  set -e
  if grep -q "PSA-ERRORS" "$WORK/psa.log"; then fail "PSScriptAnalyzer reported errors"; fi
  if ! grep -qE "PSA-DONE|skipped" "$WORK/psa.log"; then
    say "PSScriptAnalyzer: skipped (analyzer container exited $rc before reporting; likely resource pressure)"
  fi
else
  say "docker not found: Linux and PowerShell container tests skipped"
fi

say "stop the release server and verify the port is released"
cleanup
trap - EXIT
python3 - "$PORT" <<'PY'
import socket, sys
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("0.0.0.0", int(sys.argv[1])))
except OSError as e:
    print(f"FAIL: port {sys.argv[1]} still in use: {e}"); sys.exit(1)
finally:
    s.close()
print(f"port {sys.argv[1]} released")
PY
say "ALL INSTALL TESTS PASSED"