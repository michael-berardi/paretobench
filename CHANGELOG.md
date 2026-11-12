# Changelog

## 0.4.1 - 2026-11-12

- A run killed at the hard timeout now keeps its raw event stream under `PB_LOG_DIR`, like every other run. It used to
  be dropped, which left a hang with no evidence: one such run in the results below could not be explained.
- Published results: all six harnesses on a second model, short set, in
  `benchmarks/2026-11-12-harness-haiku-openrouter-short/`, and three arms on the same model through a subscription in
  `benchmarks/2026-11-12-harness-haiku-short/`.

## 0.4.0 - 2026-11-12

- New harness arm `codex`: stock Codex CLI (`codex exec --json --skip-git-repo-check --ephemeral`), found with
  `PB_CODEX_BIN` or `codex` on PATH. Each lane gets a private `CODEX_HOME` with only a generated `config.toml` built
  from the model's existing `dsh` object and `key`, so no new config keys; the key is never written to disk or argv.
  Cached tokens are subtracted from Codex's `input_tokens`; turns are tools + 1, a lower bound, because Codex reports
  usage per user turn. Added to `HARNESS_NAMES`, the models-file validation, `pb doctor` and the docs (eight adapters).
- The runner injects a model's key when the adapter sets `needs_key = True` (dsh, steak-dsh, steak-dsh-long, codex)
  instead of by the family name `dsh`. Behaviour for existing arms is unchanged; the pi family still gets no key.
- `steak-pi-lean` now matches `steak-pi run --lean` since Steak Pi 0.28.5: `--exclude-tools
  ultraterm_subagents,ultraterm_hub,todo` and `STEAK_PI_WORK_RULES_BRIEF=1`. Rows from the earlier definition (0.3.x)
  are not the same arm.
- Published results: six harnesses on one model, short set and long set, in
  `benchmarks/2026-11-12-harness-deepseek-short/` and `benchmarks/2026-11-12-harness-deepseek-long-v1/`.

## 0.3.1 - 2026-11-12

- The `long-v1` pilot ran (five arms, one model, two repeats; outcome in `tasks-long/pilot/`, rows in `benchmarks/2026-11-12-long-v1-pilot-deepseek/`). Every arm
  passed every repeat of every task, so under admission rule 6 no task is admitted on that model, the long gate was not
  run and no long-set result is published.
- Fixed the L8 prompt: it asked for `<parsed entries>` where the checker and the reference expect the number of parsed
  entries. The `long-v1` hash changes from `b9348b7c3c551ad3` to `669740c30d0f28b8`. The short set is unchanged.
- Lean gate result published in `benchmarks/2026-11-12-lean-gate-deepseek/`: `steak-pi-lean` against `steak-pi` is
  "better" (60 of 60 correct on both, cost ratio 0.46, 95% interval 0.36 to 0.63), so the arm is kept. Against stock
  `pi` there is no clear difference (cost ratio 1.07, interval 0.83 to 1.34).

## 0.3.0 - 2026-11-12

- New task set `long-v1` in `tasks-long/`: eleven long, multi-step tasks (feature, bug hunt, refactor, read-only
  scouting, mutation-judged test writing, compaction stress, hard codegen, delegated wave, edit batch, tool-loop
  recovery, finish-guard trap) on a seeded generated repository (about 9,400 lines, 7 packages, a 2 MB log), with
  hidden deterministic checkers that run outside the agent's tree, a full-tree SHA comparison, scripted reference
  solutions with recorded tool-step counts and a per-task wall budget. Select with `--task-set long-v1`; the default
  short set and its hash are unchanged. The set is unpiloted: see the admission rule and gates in
  `docs/METHODOLOGY.md`.
- `pb selftest --task-set long-v1` covers the long set: every reference passes, every untouched fixture fails, obvious
  wrong solutions fail, step counts match `steps.json`, two generations with one seed are byte-identical.
- New harness arms `steak-pi-lean` (`steak-pi` with `--exclude-tools ultraterm_subagents,todo`) and `steak-dsh-long`
  (`steak-dsh` plus the bundle's `long.patch.yml`, named error when the bundle has none).
- Reports and summaries add pass@k, pass^k, timeouts and the correct rate per repeat (`stats.pass_at_k`,
  `stats.timeouts`, `stats.per_rep_correct`).
- `--timeout` now defaults to the task set's `budgets.json` (600 s for the short set, as before).

## 0.2.3 - 2026-11-11

- Windows installer fix. `install.ps1` 0.2.2 read the user PATH unexpanded but wrote it back as a plain string, so a
  stock entry such as `%USERPROFILE%\AppData\Local\Microsoft\WindowsApps` stopped expanding and new terminals could
  lose winget and the Store Python. The PATH is now written back with its original registry type, and the change is
  broadcast. This is fixed.
- `install.ps1` now runs inside one function that is called last, so piping it into `iex` no longer leaves
  `$ErrorActionPreference = 'Stop'` or its variables in your session.
- `install.sh` uses portable `grep -e` options (the `\|` alternation was a GNU extension), only treats an existing
  launcher as its own when it mentions both `paretobench.cli` and `PARETOBENCH_TASKS`, and names the launchers it wrote.
- New tests cover these.

## 0.2.2 - 2026-11-11

- Installer fixes. On Windows the `paretobench` and `pb` launchers baked the absolute install path in ASCII, so a profile
  folder with accented characters (for example `C:\Users\José`) produced a launcher that pointed nowhere and the
  install failed after the user PATH had been changed. The launchers now locate the app relative to themselves, and
  use the OEM code page when `PARETOBENCH_BIN_DIR` puts them elsewhere. They also run in `setlocal`, so repeated runs
  no longer grow the session PYTHONPATH.
- Both installers (`install.sh`, `install.ps1`) no longer overwrite a `pb` or `paretobench` in the bin folder that they
  did not write; they say so and leave it. Launchers carry a marker line, and launchers from 0.2.0 and 0.2.1 are
  still recognised as ours and upgraded.
- `install.ps1` unpacks directly into a staging folder inside the install home (no cross-drive move out of %TEMP%),
  removes the staging folder and restores the previous release if an install is interrupted, reads the user PATH
  without expanding `%VAR%` entries, prefers the system `tar.exe`, and enables TLS 1.2 on Windows PowerShell.
  `install.sh` cleans its staging folder on every exit, restores the previous release if interrupted mid-swap, and
  only restricts the install home to its owner when it created that folder.
- New `tests/test_installers.py` covers these.

## 0.2.1 - 2026-11-11

- README results lead with the highlights: Steak Pi and Steak DSH against stock DeepSeek Harness on
  Qwen 4 Max and DeepSeek V4.1 Flash, and Steak Pi against Claude Code on Claude Haiku 5.5. Adds the
  launch-run tables from `benchmarks/2026-11-11-steak-dsh-launch`. Every figure is unchanged and matches
  the published summaries; the short-task DeepSeek table keeps its context.

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
