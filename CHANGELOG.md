# Changelog

## 0.2.0 - 2026-11-11

- One-step installers: `scripts/install.sh` (macOS, Linux) and `scripts/install.ps1` (Windows,
  also runs under PowerShell 7 on Linux). They download the release bundle, verify its SHA-256,
  install under `~/.paretobench` (`%LOCALAPPDATA%\ParetoBench` on Windows) and put `paretobench`
  and `pb` shims on the user's PATH. Python 3.11+ is required; when it is missing the installer
  names the one-line install command for the platform and stops. Re-running upgrades in place.
- `scripts/build-release.sh` builds deterministic release assets (paretobench.tar.gz, install.sh,
  install.ps1, SHA256SUMS) into `dist/release/`.
- `scripts/test-install.sh` tests the installers against a local release base on macOS, in an
  ubuntu:24.04 container and under PowerShell 7, including checksum refusal and missing or
  too-old Python.
- README gains an Install section with the two one-liners.

## 0.1.0 - 2026-11-11

Initial release. Generalized from the steak-dsh bench (same runner behaviour, tasks, checkers and
statistics), with:

- Two benches: `paretobench harness` (one model across harnesses) and `paretobench model` (one harness
  across models), sharing tasks, checkers, runner and statistics.
- Five harness adapters: pi (stock, `-ne`, no packages), steak-pi, claude-code, dsh, steak-dsh.
- Row schema adds `bench`, `harness`, `model`, `harness_version`, `pb_version`, `task_set`.
- Reports mark the Pareto frontiers (correct vs cost, correct vs time), give Wilson intervals, paired
  bootstrap ratios (5000 resamples, seed 1), exact paired sign tests and plain verdicts.
- Legacy steak-dsh rows import: old arm names map to harness names, missing task set means
  `legacy-steak-dsh-bench`, mixing task sets is refused.
- Config moved out of the repo: `~/.config/paretobench/models.json` and an optional `env` file.
- `selftest`, `doctor`, `validate` commands; `./pb` wrapper runs with no install.
