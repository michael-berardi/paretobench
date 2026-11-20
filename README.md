# ParetoBench

[![Release](https://img.shields.io/github/v/release/michael-berardi/paretobench)](https://github.com/michael-berardi/paretobench/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)](#install)

Compare coding-agent harnesses on one model, or models under one harness. For people
choosing a coding-agent setup, it measures correctness, cost and time on the same tasks,
with hidden deterministic checkers and fresh fixtures. Reports include paired bootstrap
intervals and Pareto frontiers for correctness versus cost and time.

Python 3.11+. No runtime dependencies. By [Pareto Cybernetics](https://paretocybernetics.com).

## Headline results

Claude Sonnet 5.5 subscription, short set, three repeats (2026-11-14). Cost is
list-price estimation, not subscription billing; ratios compare with Claude Code.

| Harness | Correct | Cost vs Claude Code (95%) | Time vs Claude Code (95%) |
|---|---|---|---|
| Claude Code | 60/60 | 1.00 | 1.00 |
| Codex CLI | 60/60 | 0.69 (0.64 to 0.74), better | 0.89 (0.83 to 0.95) |
| Steak DSH | 60/60 | 0.63 (0.57 to 0.71), better | 1.11 (1.05 to 1.18) |
| Steak Pi | 60/60 | 0.48 (0.44 to 0.52), better | 0.96 (0.89 to 1.03) |
| Steak Pi, lean | 60/60 | 0.49 (0.45 to 0.53), better | 0.95 (0.88 to 1.02) |

Every arm solved every task: this compares cost and time, not harder-task ability.
Codex needs an unpublished bridge you supply. [Full results and limitations](docs/RESULTS.md)
and the [live benchmarks page](https://paretocybernetics.com/benchmarks/).

## Install

macOS and Linux:

```sh
curl -fsSL https://github.com/michael-berardi/paretobench/releases/latest/download/install.sh | sh
```

Windows (PowerShell 5.1 or 7):

```powershell
irm https://github.com/michael-berardi/paretobench/releases/latest/download/install.ps1 | iex
```

Requires Python 3.11+. Downloads the bundle and verifies its SHA-256, installs `paretobench`
and `pb` in `~/.local/bin` (Windows: `%LOCALAPPDATA%\ParetoBench\bin`), and seeds
`~/.config/paretobench/models.json` if absent. Edit that config before benchmarking.
The bundle lives in `~/.paretobench/app` (Windows: `%LOCALAPPDATA%\ParetoBench\app`).
No sudo or venv. Re-run to update without replacing your config. Remove the bundle
and shims to uninstall. [Installer details and overrides](scripts/install.sh).

### From source

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

- **Local models.** A model entry may carry `"serve": {"start": [argv], "stop": [argv], "timeout": seconds}`: the
  runner runs `start` before that model's rows and `stop` after them, and runs each served model's rows as one block,
  since one machine holds one model server at a time. A failed start stops the run with `serve-failed` and the
  command's last output. With Steak Pi's local manager the commands are `steak-pi local start <id>` and
  `steak-pi local stop`; point the entry's `pi` args at `local/<id>` and set every rate to 0.

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

Part of [Pareto Cybernetics](https://paretocybernetics.com): free, private, open-source tools for working with AI agents.
