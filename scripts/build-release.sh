#!/bin/sh
# Builds the download assets for the current commit into <out> (default dist/release):
#   paretobench.tar.gz   the bundle (paretobench/, tasks/, configs/, docs/, pb, LICENSE), unpacked by install.sh and install.ps1
#   install.sh, install.ps1   the installers
#   SHA256SUMS    checksums of the three files above
# Usage: scripts/build-release.sh [out-dir]   (run from a clean checkout of the release tag)
set -eu
cd "$(dirname "$0")/.."
OUT="${1:-dist/release}"
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "build-release: the working tree has changes; build from a clean checkout" >&2; exit 1; }
commit=$(git rev-parse HEAD)
rm -rf "$OUT"; mkdir -p "$OUT"
stage=$(mktemp -d "${TMPDIR:-/tmp}/paretobench-build.XXXXXX"); trap 'rm -rf "$stage"' EXIT
git archive --format=tar HEAD paretobench tasks configs docs pb LICENSE | tar -x -C "$stage"
# Deterministic: sorted names, fixed owner and times, no gzip timestamp.
( cd "$stage" && find . -mindepth 1 | LC_ALL=C sort | sed 's|^\./||' > "$stage.list" )
if tar --version 2>/dev/null | grep -qi gnu; then
  tar -C "$stage" --owner=0 --group=0 --numeric-owner --mtime=@0 --no-recursion -cf - -T "$stage.list" | gzip -n > "$OUT/paretobench.tar.gz"
else
  COPYFILE_DISABLE=1 tar -C "$stage" --uid 0 --gid 0 --uname root --gname root --no-xattrs --no-recursion -cf - -T "$stage.list" | gzip -n > "$OUT/paretobench.tar.gz"
fi
rm -f "$stage.list"
cp scripts/install.sh scripts/install.ps1 "$OUT/"
( cd "$OUT" && if command -v sha256sum >/dev/null 2>&1; then sha256sum paretobench.tar.gz install.sh install.ps1; else shasum -a 256 paretobench.tar.gz install.sh install.ps1; fi > SHA256SUMS )
echo "built $OUT for $commit"; ls -l "$OUT"