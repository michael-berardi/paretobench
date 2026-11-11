# ParetoBench

One maintained open benchmark with two benches that share tasks, checkers, runner and statistics:

- **ParetoBench Harness**: one model across coding-agent harnesses. Which harness gets the task done
  correctly for the least cost and time? Harnesses: `pi` (stock Pi, no extensions), `steak-pi`,
  `claude-code`, `dsh` (stock DeepSeek Harness), `steak-dsh`. Comparisons are only ever made within one
  model; each model lists the harnesses that can run it.
- **ParetoBench Model**: one harness (default `steak-pi`) across models. Which model gets the task done
  correctly for the least cost and time, under identical harness, tools, prompts and effort policy?

Every report marks the Pareto frontier: no other entry is at least as correct AND at least as cheap with
one strictly better. A second frontier covers correct rate vs time. Verdicts are plain words: "better",
"worse", or "no clear difference", from paired statistics with bootstrap intervals.

Python 3.11+ standard library only. No dependencies. MIT license. By [Pareto Cybernetics](https://paretocybernetics.com).

## Results, 2026-11-11

Twenty small Python tasks, hidden deterministic checkers, every run on a fresh fixture. Raw rows and full summaries
are in [benchmarks/](benchmarks).

**ParetoBench Harness, DeepSeek V4.1 Flash** (240 runs, three repeats)

| Harness | Correct | Cost per run | Median time | Cost vs stock Pi (95% interval) |
|---|---|---|---|---|
| Pi 1.0.4 (stock) | 60/60 | $0.00060 | 14.8 s | 1.00, on both frontiers |
| Steak DSH 0.1.0 | 60/60 | $0.00088 | 21.3 s | 1.47 (1.26 to 1.70) |
| DeepSeek Harness 0.2.2-rc.1 (stock) | 60/60 | $0.00095 | 20.4 s | 1.59 (1.44 to 1.74) |
| Steak Pi 0.25.7 | 60/60 | $0.00122 | 22.5 s | 2.04 (1.71 to 2.37) |

**ParetoBench Harness, Claude Haiku 5.5** (80 runs, two repeats)

| Harness | Correct | Cost per run | Median time | Cost vs Claude Code (95% interval) |
|---|---|---|---|---|
| Claude Code 2.1.322 | 39/40 | $0.00291 | 11.4 s | 1.00 |
| Steak Pi 0.25.7 | 40/40 | $0.00233 | 19.4 s | 0.80 (0.56 to 1.17), no clear difference |

**ParetoBench Model, on Steak Pi 0.25.7** (180 runs, three repeats). One model is on a flat plan, so models are
compared in weighted tokens (input 1, cached input 0.1, cache write 1.25, output 4).

| Model | Correct | Weighted tokens per correct run | List price for 60 runs | Median time |
|---|---|---|---|---|
| Qwen 4 Max | 60/60 | 14,446, cost frontier | flat plan | 39.5 s |
| Claude Haiku 5.5 | 58/60 | 17,533 | $0.134 | 17.4 s, time frontier |
| DeepSeek V4.1 Flash | 60/60 | 17,806 | $0.074 | 18.2 s, time frontier |

Every harness and model solved nearly every task, so this task set separates entries on cost and time. It does not
show which one can solve harder problems. Tasks are short (a run is 15 to 40 seconds): features built for long
sessions cost tokens here and cannot pay back.

## Quick start (no install)

```sh
./pb validate                 # config and task files well formed
./pb doctor                   # harness executables, versions, runnable models (no model call)
./pb selftest                 # every task: check fails untouched, passes after the reference solution

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
- Executables come from env with PATH defaults: `PB_PI_BIN`, `PB_DSH_BIN`, `PB_CLAUDE_BIN`,
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

Covers the statistics (bootstrap determinism, Wilson, sign test, frontier, verdict rule), legacy row
import, task-set mixing refusal, config validation, command construction for all five harnesses with
fake executables (keys never in argv), resume, and stop cleanup with a fake slow harness.

## License

MIT, Pareto Cybernetics. See [LICENSE](LICENSE).
