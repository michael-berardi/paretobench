# ParetoBench

One maintained open benchmark with two benches that share tasks, checkers, runner and statistics:

- **ParetoBench Harness**: one model across coding-agent harnesses. Which harness gets the task done
  correctly for the least cost and time? Harnesses: `pi` (stock Pi, no extensions), `steak-pi`,
  `claude-code`, `dsh` (stock DeepSeek Harness), `steak-dsh`, and `codex` (stock Codex CLI), plus the extra arms `steak-pi-lean` and
  `steak-dsh-long` (eight adapters in all). Comparisons are only ever made within one
  model; each model lists the harnesses that can run it.
- **ParetoBench Model**: one harness (default `steak-pi`) across models. Which model gets the task done
  correctly for the least cost and time, under identical harness, tools, prompts and effort policy?

Every report marks the Pareto frontier: no other entry is at least as correct AND at least as cheap with
one strictly better. A second frontier covers correct rate vs time. Verdicts are plain words: "better",
"worse", or "no clear difference", from paired statistics with bootstrap intervals.

Python 3.11+ standard library only. No dependencies. MIT license. By [Pareto Cybernetics](https://paretocybernetics.com).

## Results, 2026-11-12: six harnesses on one model

Stock Pi, Codex CLI, stock DeepSeek Harness, Steak DSH 0.3.3, Steak Pi 0.28.5 and Steak Pi run lean
(`steak-pi run --lean`), all on DeepSeek V4.1 Flash, three repeats, paired on task and repeat. Rows and summaries:
[short set](benchmarks/2026-11-12-harness-deepseek-short), [long set](benchmarks/2026-11-12-harness-deepseek-long-v1).

| Harness | Short set: correct | Short set: cost vs stock Pi (95%) | Long set: correct | Long set: cost vs stock Pi (95%) |
|---|---|---|---|---|
| Stock Pi | 60/60 | 1.00 | 33/33 | 1.00 |
| Steak Pi, lean | 60/60 | 0.80 (0.67 to 0.96), better | 32/33 | 0.80 (0.63 to 1.00), no clear difference |
| Steak DSH | 60/60 | 1.01 (0.81 to 1.22), no clear difference | 33/33 | 1.20 (0.89 to 1.69), no clear difference |
| Stock DeepSeek Harness | 60/60 | 1.41 (1.16 to 1.70), worse | 33/33 | 1.50 (1.26 to 1.84), worse |
| Steak Pi, default | 60/60 | 1.55 (1.33 to 1.79), worse | 33/33 | 0.88 (0.64 to 1.15), no clear difference |
| Codex CLI | 60/60 | 2.43 (1.96 to 2.99), worse | 32/33 | 2.09 (1.68 to 2.64), worse |

- Steak DSH against stock DeepSeek Harness: 0.71 times the cost on the short set (0.62 to 0.83), better; 0.80 times on
  the long set (0.63 to 1.02), no clear difference, and 0.68 times the time (0.60 to 0.79).
- Every Steak arm, and stock Pi, was cheaper than Codex CLI on both sets (0.33 to 0.64 times its cost).
- What this does not show: one model, one machine. Every harness solved nearly everything, so this compares cost and
  time, not ability on hard problems. The long set did not separate harnesses on correctness in its pilot, so its
  correct counts carry little weight; the two misses were both on the same task (L6). Codex CLI ran stock with an
  empty home on a model it was not built for, and its turn count is a lower bound.

**Quality, speed and cost together, 2026-11-12.** Stock Pi, Codex CLI, stock DeepSeek Harness, Steak DSH 0.5.0 and
Steak Pi 0.29.0, each with no flags, on DeepSeek V4.1 Flash, three repeats, paired. Ratios are against stock Pi; below
1.00 is cheaper or faster. Rows: [short](benchmarks/2026-11-12-triple-deepseek-short),
[long](benchmarks/2026-11-12-triple-deepseek-long-v1),
[long, reasoning off](benchmarks/2026-11-12-triple-deepseek-long-v1-reasoning-off).

| Harness | Short: correct | Short: cost | Short: time | Long: correct | Long: cost | Long: time |
|---|---|---|---|---|---|---|
| Stock Pi | 60/60 | 1.00 | 1.00 | 33/33 | 1.00 | 1.00 |
| Steak Pi | 60/60 | 1.04 (0.94 to 1.15) | 1.10 (0.88 to 1.37) | 33/33 | 0.85 (0.74 to 1.03) | 0.83 (0.64 to 1.09) |
| Steak DSH | 60/60 | 1.05 (0.95 to 1.18) | 1.09 (0.86 to 1.39) | 31/33 | 1.07 (0.83 to 1.36) | 1.03 (0.82 to 1.31) |
| Stock DeepSeek Harness | 60/60 | 1.64 (1.46 to 1.82) | 1.37 (1.06 to 1.73) | 33/33 | 1.73 (1.23 to 2.58) | 1.47 (1.02 to 2.08) |
| Codex CLI | 60/60 | 2.24 (1.88 to 2.62) | 1.58 (1.28 to 1.94) | 32/33 | 1.81 (1.40 to 2.21) | 2.45 (1.72 to 3.65) |

- Steak Pi and Steak DSH are level with stock Pi on all three axes: no interval excludes 1.00, and no quality
  difference excludes zero. Stock DeepSeek Harness and Codex CLI are worse than stock Pi on cost and on time.
- Steak DSH against stock DeepSeek Harness: 0.64 times the cost on short tasks (0.58 to 0.72) and, on long tasks, 0.62
  times the cost (0.43 to 0.90) and 0.70 times the time (0.53 to 0.93), with 31 of 33 correct against 33 of 33. Both
  misses were one task (L6); eight more repeats of it gave Steak DSH 8 of 8.
- Quality: to move correctness off the ceiling the long set was run with reasoning switched off. Correct out of 33:
  Codex CLI 32, Steak Pi 31, stock Pi 30, Steak DSH 29, stock DeepSeek Harness 28. No paired difference excludes zero
  (the intervals are about 15 points either way), so this does not rank the harnesses on quality.
- One model, one machine, one benchmark at a time. Time is comparable within a run, not across runs.

**A second model, all six harnesses, 2026-11-12.** Claude Haiku 5.5 on a per-token route, short set, three repeats
([rows](benchmarks/2026-11-12-harness-haiku-openrouter-short)).

| Harness | Correct | Cost vs stock Pi (95%) |
|---|---|---|
| Stock Pi | 60/60 | 1.00 |
| Steak Pi, lean | 60/60 | 0.83 (0.65 to 1.03), no clear difference |
| Steak Pi, default | 59/60 | 0.94 (0.77 to 1.15), no clear difference |
| Steak DSH | 60/60 | 1.34 (1.19 to 1.51), worse |
| Stock DeepSeek Harness | 60/60 | 1.41 (1.22 to 1.64), worse |
| Codex CLI | 60/60 | 1.94 (1.56 to 2.38), worse |

- Steak DSH against stock DeepSeek Harness: 0.95 times the cost (0.84 to 1.10), no clear difference. Its clear win on
  the first model (0.71 times) did not carry over to this one.
- Steak Pi run lean against the default run: 0.88 times the cost (0.77 to 1.00), better.
- Every other arm was cheaper than Codex CLI (0.43 to 0.73 times its cost).
- The one Steak Pi miss was a run killed at the 600-second hard timeout with nothing recorded, not a wrong answer. The
  same task run 12 more times finished 12 of 12 in at most 23 seconds, so the cause is unknown. The runner used to
  drop the log of a timed-out run; since 0.4.1 it keeps it.

**The same model on a subscription, 2026-11-12.** Short set, three repeats
([rows](benchmarks/2026-11-12-harness-haiku-short)). Only three arms can reach the model this way: Steak Pi 0.28.5,
Steak Pi run lean, and Claude Code. Cost uses the model's list prices.

| Harness | Correct | Cost vs Claude Code (95%) |
|---|---|---|
| Claude Code | 60/60 | 1.00 |
| Steak Pi, default | 60/60 | 0.55 (0.49 to 0.60), better |
| Steak Pi, lean | 58/60 | 0.50 (0.43 to 0.57), no clear difference because of the two misses |

The lean run against the default run cost 0.92 times as much (0.82 to 1.01), no clear difference. Both lean misses were
one task (h5, a sum over a log): the model printed a line count beside the sum and reported the count. Ten more repeats
of that task gave the default run 8 of 10 and the lean run 10 of 10, so the slip is the model's on both, not the lean
run's.

## Results, 2026-11-11

Twenty small Python tasks, hidden deterministic checkers, every run on a fresh fixture. Raw rows and full summaries
are in [benchmarks/](benchmarks). The same results are on the
[Pareto Cybernetics benchmarks page](https://paretocybernetics.com/benchmarks/).

Highlights:

- On Qwen 4 Max, Steak Pi was the cheapest and fastest harness: 0.67× the weighted tokens of stock DeepSeek
  Harness (95% interval 0.60 to 0.74) and 0.67× the time, 100 of 100 correct, on both Pareto frontiers.
- Steak DSH beat stock DeepSeek Harness on the same model: 0.70× the weighted tokens on Qwen 4 Max (0.62 to 0.78)
  and 0.84× the cost on DeepSeek V4.1 Flash (0.76 to 0.93), every run correct.
- Against Claude Code on Claude Haiku 5.5, Steak Pi solved 40 of 40 to Claude Code's 39 of 40, was cheaper in
  35 of 40 paired runs and sent about half the input tokens (0.49×).
- The Pi family led on short DeepSeek tasks: stock Pi, the base Steak Pi is built on, had the lowest cost and
  time of the four harnesses.

**Qwen 4 Max: Steak Pi and Steak DSH against stock DSH** (300 runs, five repeats, legacy-steak-dsh-bench task
set; flat plan, so cost is in weighted tokens per correct run)

| Harness | Correct | Weighted tokens | Median time | vs stock DSH (95% interval) |
|---|---|---|---|---|
| Steak Pi 0.25.7 | 100/100 | 12,807 | 30.9 s | 0.67 (0.60 to 0.74), better, on both frontiers |
| Steak DSH 0.1.0 | 100/100 | 13,395 | 42.1 s | 0.70 (0.62 to 0.78), better |
| DeepSeek Harness 0.2.2-rc.1 (stock) | 100/100 | 19,248 | 48.1 s | 1.00 |

**DeepSeek V4.1 Flash: Steak DSH against stock DSH** (same 300-run launch set)

| Harness | Correct | Cost per run | Median time | Cost vs stock DSH (95% interval) |
|---|---|---|---|---|
| Steak DSH 0.1.0 | 100/100 | $0.00089 | 17.5 s | 0.84 (0.76 to 0.93), better, on both frontiers |
| Steak Pi 0.25.7 | 100/100 | $0.00121 | 18.2 s | 1.14 (0.99 to 1.29), no clear difference |
| DeepSeek Harness 0.2.2-rc.1 (stock) | 100/100 | $0.00106 | 18.9 s | 1.00 |

In the 60-pair ParetoBench run below, Steak DSH was again cheaper than stock DSH (0.92×, 0.81 to 1.06); over all
160 pairs it is 0.87× (0.80 to 0.94).

**ParetoBench Harness, Claude Haiku 5.5** (80 runs, two repeats)

| Harness | Correct | Cost per run | Median time | Cost vs Claude Code (95% interval) |
|---|---|---|---|---|
| Steak Pi 0.25.7 | 40/40 | $0.00233 | 19.4 s | 0.80 (0.56 to 1.17), cheaper in 35 of 40 pairs |
| Claude Code 2.1.322 | 39/40 | $0.00291 | 11.4 s | 1.00 |

Steak Pi sent 0.49× the input tokens and 0.65× the output tokens of Claude Code. A second 80-run comparison on the
launch task set gave 0.78× (0.61 to 1.04), cheaper in 38 of 40 pairs. Both intervals cross 1.00, so the strict
verdict is no clear difference. Claude Code was faster per run.

**ParetoBench Harness, DeepSeek V4.1 Flash, short tasks** (240 runs, three repeats)

| Harness | Correct | Cost per run | Median time | Cost vs stock Pi (95% interval) |
|---|---|---|---|---|
| Pi 1.0.4 (stock) | 60/60 | $0.00060 | 14.8 s | 1.00, on both frontiers |
| Steak DSH 0.1.0 | 60/60 | $0.00088 | 21.3 s | 1.47 (1.26 to 1.70) |
| DeepSeek Harness 0.2.2-rc.1 (stock) | 60/60 | $0.00095 | 20.4 s | 1.59 (1.44 to 1.74) |
| Steak Pi 0.25.7 | 60/60 | $0.00122 | 22.5 s | 2.04 (1.71 to 2.37) |

Every harness solved every task. Stock Pi, the base Steak Pi builds on, was the cheapest and fastest. Steak Pi's
parallel workers, compaction and checks are built for long sessions; a 20-second task pays their prompt cost
without using them.

**ParetoBench Model, on Steak Pi 0.25.7** (180 runs, three repeats). One model is on a flat plan, so models are
compared in weighted tokens (input 1, cached input 0.1, cache write 1.25, output 4).

| Model | Correct | Weighted tokens per correct run | List price for 60 runs | Median time |
|---|---|---|---|---|
| Qwen 4 Max | 60/60 | 14,446, cost frontier | flat plan | 39.5 s |
| Claude Haiku 5.5 | 58/60 | 17,533 | $0.134 | 17.4 s, time frontier |
| DeepSeek V4.1 Flash | 60/60 | 17,806 | $0.074 | 18.2 s, time frontier |

Steak Pi held 178 of 180 runs correct across three model families. These tasks are short (a run is 15 to 40
seconds), so they separate entries on cost and time, not on which one can solve harder problems.

## Task sets

- `short` (default): the 20 small tasks behind every published result above. Unchanged.
- `long-v1`: eleven long, multi-step tasks on a seeded, generated multi-package Python repository (about 9,400 lines,
  7 packages, a green `unittest` suite, 2 MB of logs): multi-file feature, bug hunt, refactor, read-only scouting with
  exact answers, mutation-judged test writing, compaction stress, hard codegen, a delegated wave, a batch of edits,
  tool-loop recovery and a finish-guard trap. Hidden deterministic checkers run outside the agent's tree; read-only
  tasks are judged by a full-tree SHA manifest. Select it with `--task-set long-v1` on `harness`, `model`, `selftest`
  and `validate`; the hard timeout defaults to 30 minutes (60 for L6) from `tasks-long/budgets.json`. Status: built,
  selftested and piloted on one model, where **every harness passed every task**, so it does not separate harnesses
  there and no results are published for it (`tasks-long/pilot/`). See
  [docs/METHODOLOGY.md](docs/METHODOLOGY.md#the-long-task-set-long-v1) for the tasks, the admission rule and the gates.

Three extra harness arms exist: `steak-pi-lean` (the `steak-pi` arm the way `steak-pi run --lean` runs it since Steak
Pi 0.28.5: `--exclude-tools ultraterm_subagents,ultraterm_hub,todo` and `STEAK_PI_WORK_RULES_BRIEF=1`),
`codex` (stock Codex CLI on the model's `dsh` route; no new config keys, see METHODOLOGY) and `steak-dsh-long` (the `steak-dsh` arm plus the bundle's
`long.patch.yml`; a bundle without it stops the run with a named error). List them under `harnesses` in a model entry
to use them. Reports also print pass@k, pass^k, timeouts and the correct rate per repeat.

## Install

One line, no checkout needed:

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

Manual route (from a checkout): `./pb ...` runs with no install, or `pip install .` for the
`paretobench` console script; an installed copy finds the task set through `PARETOBENCH_TASKS`.

## Quick start (no install)

```sh
./pb validate                 # config and task files well formed
./pb doctor                   # harness executables, versions, runnable models (no model call)
./pb selftest                 # every task: check fails untouched, passes after the reference solution

# Long set: eleven long multi-step tasks on a generated 9,400-line repository
./pb selftest --task-set long-v1      # 11 references pass, untouched fixtures fail, deterministic fixture
./pb harness --model qwen --harnesses steak-pi,pi --task-set long-v1 --reps 5 --par 2 --out runs/long1

# Harness bench: one model, several harnesses
./pb harness --model qwen --harnesses pi,steak-pi,dsh,steak-dsh --reps 3 --par 2 --out runs/run1
./pb report runs/run1 --md

# Model bench: one harness, several models
./pb model --harness steak-pi --models qwen,deepseek --reps 3 --par 2 --out runs/run2
./pb report runs/run2 --md
```

`paretobench` is also a console script (`pip install .`); an installed copy finds the task set through
`PARETOBENCH_TASKS` when it is not run from this repo.

## Configuration

No machine-specific path or secret lives in this repo.

- `configs/models.example.json` documents the models schema with placeholder routes.
- The real file is `$PARETOBENCH_CONFIG` or `~/.config/paretobench/models.json`: per model, a `harnesses`
  list, per-harness settings (`pi` model args, optional `steak_pi_extra`, `claude` args, a `dsh` route,
  `key.auth`/`key.env`) and one `rates` table applied to every harness.
- Executables come from env with PATH defaults: `PB_PI_BIN`, `PB_DSH_BIN`, `PB_CLAUDE_BIN`, `PB_CODEX_BIN`,
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

## Results

`benchmarks/` holds published raw rows and summaries, one folder per dated run. `paretobench report DIR`
works for both benches (it detects which from the rows), reads legacy steak-dsh arm names
(`dsh`, `sdsh`, `sp`, `cc`), treats rows without a task-set hash as the legacy set, and refuses to mix
task sets. It writes `summary.json` and `summary.md` into the dir.

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
