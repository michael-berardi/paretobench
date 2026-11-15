# ParetoBench

Compare coding-agent harnesses on one model, or models under one harness. For people
choosing a coding-agent setup, it measures correctness, cost and time on the same tasks,
with hidden deterministic checkers and fresh fixtures. Reports include paired bootstrap
intervals and Pareto frontiers for correctness versus cost and time.

Python 3.11+. No runtime dependencies. [MIT license](LICENSE).

## Install

macOS and Linux:

```sh
curl -fsSL https://github.com/michael-berardi/paretobench/releases/latest/download/install.sh | sh
```

Windows (PowerShell 5.1 or 7):

```powershell
irm https://github.com/michael-berardi/paretobench/releases/latest/download/install.ps1 | iex
```

What it does: downloads the release bundle, verifies its SHA-256 before installing anything, and puts
`paretobench` (and `pb`) in `~/.local/bin` (`%LOCALAPPDATA%\ParetoBench\bin` on Windows, added to your
user PATH). The bundle (package, tasks, configs, docs) lives in `~/.paretobench/app`
(`%LOCALAPPDATA%\ParetoBench\app` on Windows). Needs Python 3.11 or newer already installed; there are
no dependencies, so no venv is created. If no suitable Python is found the installer names the one-line
command that installs it (`brew`, `apt`, `winget`) and stops. If `~/.config/paretobench/models.json` does
not exist yet, the documented example config is copied there; edit it with your own models and routes
before running a bench. The installer finishes with `paretobench validate` and `paretobench doctor`
(missing harness executables are reported but do not fail the install).

Update: re-run the same one-liner; it upgrades in place and keeps your config. Remove: delete
`~/.paretobench` (or `%LOCALAPPDATA%\ParetoBench`) and the `paretobench`/`pb` shims in the bin folder.
No sudo, no shell-profile edits. Overrides: `PARETOBENCH_HOME`, `PARETOBENCH_BIN_DIR`,
`PARETOBENCH_VERSION` (pin a release), `PARETOBENCH_RELEASE_BASE` (download base, used by tests).

From a checkout, `./pb` needs no install. `pip install .` installs the console script only;
set `PARETOBENCH_TASKS` to the checkout’s `tasks/` directory to use its task sets.

## First use

After installing, run the offline checks. They do not call a model:

```sh
paretobench validate
paretobench selftest
paretobench selftest --task-set long-v1
```

From a fresh checkout, use `./pb` instead of `paretobench`. Validate the example config with
`PARETOBENCH_CONFIG=configs/models.example.json ./pb validate`; no local config is seeded
until you run the installer.

Edit the seeded models config with your routes and rates, install the harnesses you want
to compare, then run `paretobench doctor`. Benchmark commands below **call models and may
incur charges**; replace the example model keys with keys from your config:

```sh
paretobench harness --model example-paid --harnesses pi,steak-pi --reps 3 --par 2 --out runs/run1
paretobench report runs/run1 --md
paretobench model --harness steak-pi --models example-flat,example-paid --reps 3 --par 2 --out runs/run2
paretobench report runs/run2 --md
```

## Published results and task sets

[Published tables and limitations](docs/RESULTS.md) link to the unchanged raw rows and
summaries in [benchmarks/](benchmarks). These are historical runs, not current rankings.
`report DIR` writes `summary.json` and `summary.md` into DIR; copy published rows to a
scratch directory before generating a new report.

- `short` (default): 20 small Python tasks, mainly measuring overhead and reliability.
- `long-v1`: eleven multi-step tasks on a seeded multi-package Python fixture. Select with
  `--task-set long-v1` on `harness`, `model`, `validate` or `selftest`. Default hard budgets
  are 30 minutes per task, 60 for L6. The pilot passed every task in every arm, so it did
  not establish quality discrimination. Later exploratory long-set results are published;
  they do not establish that the admission gate passed.

Eight adapters: `pi`, `steak-pi`, `claude-code`, `dsh`, `steak-dsh`, `codex`,
`steak-pi-lean`, `steak-dsh-long`. A model's `harnesses` list controls availability.
Subscription Codex needs a bridge you supply; none is shipped. Exact commands, adapter
requirements, task definitions and statistical limits are in [the methodology](docs/METHODOLOGY.md).

## Configuration

No machine-specific path or secret lives in this repo.

- `configs/models.example.json` documents the models schema with placeholder routes.
- The real file is `$PARETOBENCH_CONFIG` or `~/.config/paretobench/models.json`: per model, a `harnesses`
  list, per-harness settings (`pi` model args, optional `steak_pi_extra`, `claude` args, a `dsh` route,
  `key.auth`/`key.env`) and one `rates` table applied to every harness.
- Executables come from env with PATH defaults: `PB_PI_BIN`, `PB_DSH_BIN`, `PB_CLAUDE_BIN`, `PB_CODEX_BIN`,
  `PB_CODEX_BRIDGE` (only for the codex arm on a Claude Code subscription model: a bridge script you supply, see
  docs/METHODOLOGY.md; unset stops that arm with `codex-bridge-unset`),
  `PB_STEAK_PI_PACKAGE` (the Steak Pi package dir), `PB_STEAK_DSH_PATCH` (the bundle's cordis.patch.yml),
  `PB_PI_AGENT_DIR` (where auth.json/models.json are read; default `~/.pi/agent`).
- `~/.config/paretobench/env` (KEY=VALUE lines) is loaded by the CLI when present, so machine paths stay
  out of the repo and out of your shell history.

Keys are read from the Pi agent auth store at run time, passed only via the child environment, never
printed, stored or put on a command line, and scrubbed from raw logs (`PB_LOG_DIR`).

## What a run does

Fresh fixture per run. Private per-process work dir removed on exit. Hard timeout that kills the whole
child process group. Balanced entry order per (rep, task). One warm-up per lane; an arm whose every
warm-up fails aborts with a named error. Resume from existing rows. Rate-limit retries (30 s then 90 s,
at most 2). Failures stay in the sample as incorrect runs. See [docs/METHODOLOGY.md](docs/METHODOLOGY.md)
for the full method, the exact commands per harness, the statistics and the limits.

## Tests

```sh
python3 -m unittest discover -s tests
```

Covers the statistics (bootstrap determinism, Wilson, sign test, frontier, verdict rule, pass@k, timeouts, per-repeat
correct), the long set (deterministic generator, every reference passes, every untouched fixture fails, a runner run
through scripted agents), legacy row
import, task-set mixing refusal, config validation, command construction for all eight harnesses with
fake executables (keys never in argv), resume, and stop cleanup with a fake slow harness.

## License

MIT, Pareto Cybernetics. See [LICENSE](LICENSE).
