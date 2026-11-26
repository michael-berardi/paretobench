<!-- update-contract: v1 -->
# Updates

ParetoBench tells you when a newer stable release exists and makes installing it one step.
Automatic installation is opt-in. What the check sends is in [PRIVACY.md](../PRIVACY.md).

## The notice

Once a day, an interactive command checks for a newer release in the background. If it finds
one, two lines follow the command's output on stderr:

```text
paretobench 0.9.0 available (you have 0.8.0) · run: paretobench update
turn on automatic updates: paretobench update --auto on · skip: paretobench update --skip
```

A version is shown at most once a day, and never after `update --skip`; a newer release
notifies again. The notice never appears in `--json` output, results files, or after a failed
command. There is no check or notice when stdout or stderr is not a terminal, when `CI` is set,
inside an agent shell (Claude Code, Codex), with `PARETOBENCH_NO_UPDATE_CHECK=1`, or with
`"check_automatically": false` in `~/.config/paretobench/settings.json`.

## Commands

```sh
paretobench update              # show current → new and the release notes, then install
paretobench update --check      # exit 0 current, 10 update available, 1 check failed (cause on stderr)
paretobench update --skip       # hide this version's notice
paretobench update --auto on    # install future updates automatically (off by default)
paretobench update --auto off
paretobench update --auto status
paretobench update --rollback   # restore the previous release (installer bundle only)
```

On a terminal, `update` asks `Install <new> now? [Y/n]`, and after the first install asks
once `Install future updates automatically? [y/N]`. Without a terminal, or with `--yes`, it
installs without questions. The new version applies on the next start.

With automatic updates on, the daily check installs a new release in a detached, low-priority
process instead of showing the notice. Its output goes to `auto-update.log` next to the cache
file and is replaced on each run. A failed automatic install keeps the current version, shows
the notice again, and `update --check` prints the cause.

## How each install is updated

- **Installer bundle** (`install.sh`, `install.ps1`): `update` downloads the release's
  `paretobench.tar.gz` and `SHA256SUMS`, checks the SHA-256 before unpacking, checks that the
  new copy starts and reports the expected version, then swaps it in. The previous release
  stays as `app.previous` for `update --rollback` until the new version has run a command
  successfully, and seven days at most. Download files are removed whether the install
  succeeds or fails.
- **uv tool, pipx, pip**: `update` runs the package manager, pinned to the release tag on
  GitHub (for example `uv tool install --force git+https://github.com/michael-berardi/paretobench@v0.9.0`).
  The PyPI package named `paretobench` is a different project and is never installed. Task
  sets still come from `PARETOBENCH_TASKS`, so update that checkout too.
- **Source checkout** (`./pb`): the notice says `git pull`; `update` changes nothing.

## Files and uninstall

The check writes one small cache file: `~/Library/Caches/paretobench/updates.json` (macOS),
`~/.cache/paretobench/updates.json` (Linux, or `$XDG_CACHE_HOME`), or
`%LOCALAPPDATA%\paretobench\Cache\updates.json` (Windows). Your switches are in
`~/.config/paretobench/settings.json`. To uninstall completely, run `paretobench update --auto off`,
then remove the bundle and shims, that cache folder and `~/.config/paretobench`.

`PARETOBENCH_UPDATE_API`, `PARETOBENCH_UPDATE_CACHE` and `PARETOBENCH_SETTINGS` point the
check, the cache and the settings elsewhere; they exist for tests.
