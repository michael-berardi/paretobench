#!/bin/sh
# ParetoBench installer for macOS and Linux:  curl -fsSL https://github.com/michael-berardi/paretobench/releases/latest/download/install.sh | sh
# Downloads the latest release (a small pure-Python bundle), checks its SHA-256, and puts `paretobench` (and `pb`)
# on your PATH. Needs Python 3.11+ already on this machine; there are no dependencies, so no venv is created.
# Layout: $PARETOBENCH_HOME/app holds the release (paretobench/, tasks/, configs/, docs/, pb).
# Environment: PARETOBENCH_HOME (default ~/.paretobench), PARETOBENCH_BIN_DIR (default ~/.local/bin),
# PARETOBENCH_VERSION (default: latest, e.g. 0.1.0), PARETOBENCH_RELEASE_BASE (override the download base URL, used by tests).
set -eu

REPO="michael-berardi/paretobench"
HOME_DIR="${PARETOBENCH_HOME:-$HOME/.paretobench}"
case "$HOME_DIR" in /*) ;; *) HOME_DIR="$(pwd)/$HOME_DIR" ;; esac
APP="$HOME_DIR/app"
BIN_DIR="${PARETOBENCH_BIN_DIR:-$HOME/.local/bin}"
case "$BIN_DIR" in /*) ;; *) BIN_DIR="$(pwd)/$BIN_DIR" ;; esac
if [ -n "${PARETOBENCH_RELEASE_BASE:-}" ]; then BASE="$PARETOBENCH_RELEASE_BASE"
elif [ -n "${PARETOBENCH_VERSION:-}" ]; then BASE="https://github.com/$REPO/releases/download/v${PARETOBENCH_VERSION#v}"
else BASE="https://github.com/$REPO/releases/latest/download"; fi

say() { printf '%s\n' "$*"; }
die() { printf 'paretobench install: %s\n' "$*" >&2; exit 1; }

main() {
command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 || die "needs curl or wget"
if command -v curl >/dev/null 2>&1; then fetch() { curl -fsSL --retry 3 -o "$2" "$1" || die "download failed: $1"; }
else fetch() { wget -q -O "$2" "$1" || die "download failed: $1"; }; fi
command -v tar >/dev/null 2>&1 || die "needs tar"
if command -v sha256sum >/dev/null 2>&1; then sha256() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }
else die "needs sha256sum or shasum"; fi

# Python 3.11+ on this machine; there are no dependencies, so the system Python is used directly.
case "$(uname -s)" in
  Darwin) PY_HINT="brew install python@3.13" ;;
  Linux)  PY_HINT="sudo apt-get install -y python3 (or your distribution's equivalent)" ;;
  *)      PY_HINT="your system's package manager (on Windows use install.ps1)" ;;
esac
PYTHON=""
for c in python3.13 python3.12 python3.11 python3; do
  p=$(command -v "$c" 2>/dev/null) || continue
  if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    PYTHON="$p"; break
  fi
done
[ -n "$PYTHON" ] || die "needs Python 3.11 or newer and none was found; install it with: $PY_HINT"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/paretobench-install.XXXXXX") || die "cannot create a temporary folder"
trap 'rm -rf "$TMP"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# expect <file> <name> <sums-file>: the file's SHA-256 must equal the line for <name> in the sums file.
expect() {
  want=$(awk -v n="$2" '{ f=$2; sub(/^\*/, "", f); if (f == n) print $1 }' "$3")
  [ -n "$want" ] || die "no checksum for $2 in $(basename "$3")"
  [ "$(sha256 "$1")" = "$want" ] || die "checksum mismatch for $2; nothing was installed"
}

say "Downloading ParetoBench..."
fetch "$BASE/paretobench.tar.gz" "$TMP/paretobench.tar.gz"
fetch "$BASE/SHA256SUMS" "$TMP/SHA256SUMS"
expect "$TMP/paretobench.tar.gz" paretobench.tar.gz "$TMP/SHA256SUMS"
mkdir "$TMP/src"
tar -xzf "$TMP/paretobench.tar.gz" -C "$TMP/src" || die "cannot unpack the download"
[ -f "$TMP/src/paretobench/cli.py" ] && [ -f "$TMP/src/tasks/tasks.json" ] || die "the download is not a ParetoBench release"
VERSION=$(sed -n 's/^__version__ = "\([^"]*\)".*/\1/p' "$TMP/src/paretobench/__init__.py" | head -n 1)
[ -n "$VERSION" ] || die "cannot read the release version"

# Stage inside PARETOBENCH_HOME so the final move is a same-filesystem rename; nothing is half-installed.
mkdir -p "$HOME_DIR" "$BIN_DIR"
chmod 700 "$HOME_DIR" 2>/dev/null || true
STAGE="$HOME_DIR/.app.new.$$"
rm -rf "$STAGE"
mv "$TMP/src" "$STAGE"
got=$(PYTHONPATH="$STAGE" PARETOBENCH_TASKS="$STAGE/tasks" "$PYTHON" -m paretobench.cli --version 2>&1) \
  || { rm -rf "$STAGE"; die "the new copy does not start: $got"; }
case "$got" in
  "paretobench $VERSION") ;;
  *) rm -rf "$STAGE"; die "the new copy reports '$got', not paretobench $VERSION; nothing was changed" ;;
esac
say "Installing ParetoBench $VERSION..."
rm -rf "$HOME_DIR/app.old"
if [ -d "$APP" ]; then mv "$APP" "$HOME_DIR/app.old"; fi
mv "$STAGE" "$APP" || { [ ! -d "$HOME_DIR/app.old" ] || mv "$HOME_DIR/app.old" "$APP"; die "cannot move the release into $APP"; }
rm -rf "$HOME_DIR/app.old"

# The models config lives outside the install so upgrades keep it. Seed the documented example when absent.
MODELS="${PARETOBENCH_CONFIG:-$HOME/.config/paretobench/models.json}"
if [ ! -f "$MODELS" ]; then
  mkdir -p "$(dirname "$MODELS")"
  cp "$APP/configs/models.example.json" "$MODELS"
  say "Seeded example models config at $MODELS; edit it with your own models and routes before running a bench."
fi

# Shims: run the installed copy with the right PYTHONPATH and task set; a user-set PARETOBENCH_TASKS wins.
for name in paretobench pb; do
  cat > "$BIN_DIR/$name.tmp.$$" <<SHIM
#!/bin/sh
# ParetoBench launcher, written by install.sh. Re-run the installer to upgrade.
PARETOBENCH_TASKS="\${PARETOBENCH_TASKS:-$APP/tasks}"
PYTHONPATH="$APP\${PYTHONPATH:+:\$PYTHONPATH}"
export PARETOBENCH_TASKS PYTHONPATH
exec "$PYTHON" -m paretobench.cli "\$@"
SHIM
  chmod 755 "$BIN_DIR/$name.tmp.$$"
  mv -f "$BIN_DIR/$name.tmp.$$" "$BIN_DIR/$name"
done

say "ParetoBench $VERSION installed ($BIN_DIR/paretobench, $BIN_DIR/pb)."
"$BIN_DIR/paretobench" validate || die "paretobench validate failed after install (see the error above)"
say "Checking harness executables (paretobench doctor):"
if "$BIN_DIR/paretobench" doctor; then :
else say "doctor: some harness executables are missing; that is fine for installing. Add them before running a bench."; fi
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) say "Add $BIN_DIR to your PATH:  export PATH=\"$BIN_DIR:\$PATH\"" ;; esac
say "Next: paretobench selftest"
}

main "$@"