# Published results

[Setup and usage](../README.md) · [Methodology](METHODOLOGY.md)

## Results, 2026-11-14: five harnesses on Claude Sonnet 5.5 (subscription)

Claude Code, Codex CLI, Steak DSH, Steak Pi 0.29.0 and Steak Pi run lean, all on Claude Sonnet 5.5 through one Claude
Code login, short set, three repeats, paired on task and repeat. Cost is list price, an estimate on a subscription.
Ratios are against Claude Code; below 1.00 is cheaper or faster. Rows and write-up:
[rows](../benchmarks/2026-11-14-harness-sonnet-short).

| Harness | Correct | Cost vs Claude Code (95%) | Time vs Claude Code (95%) |
|---|---|---|---|
| Claude Code | 60/60 | 1.00 | 1.00 |
| Codex CLI | 60/60 | 0.69 (0.64 to 0.74), better | 0.89 (0.83 to 0.95) |
| Steak DSH | 60/60 | 0.63 (0.57 to 0.71), better | 1.11 (1.05 to 1.18) |
| Steak Pi | 60/60 | 0.48 (0.44 to 0.52), better | 0.96 (0.89 to 1.03) |
| Steak Pi, lean | 60/60 | 0.49 (0.45 to 0.53), better | 0.95 (0.88 to 1.02) |

- Every arm solved every task, so correctness does not separate them. Steak Pi was cheapest ($0.0097 per run at list
  price); Codex CLI had the lowest median time (8.4 s against 9.4 s for Claude Code).
- Codex CLI ran through a local bridge onto the same login; the bridge is not published. The arm needs a bridge you
  supply (`PB_CODEX_BRIDGE`).
- Not run: stock Pi and stock DeepSeek Harness, which cannot use a subscription route. One model, short set at
  ceiling, three repeats.

## Results, 2026-11-12: six harnesses on one model

Stock Pi, Codex CLI, stock DeepSeek Harness, Steak DSH 0.3.3, Steak Pi 0.28.5 and Steak Pi run lean
(`steak-pi run --lean`), all on DeepSeek V4.1 Flash, three repeats, paired on task and repeat. Rows and summaries:
[short set](../benchmarks/2026-11-12-harness-deepseek-short), [long set](../benchmarks/2026-11-12-harness-deepseek-long-v1).

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
1.00 is cheaper or faster. Rows: [short](../benchmarks/2026-11-12-triple-deepseek-short),
[long](../benchmarks/2026-11-12-triple-deepseek-long-v1),
[long, reasoning off](../benchmarks/2026-11-12-triple-deepseek-long-v1-reasoning-off).

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
([rows](../benchmarks/2026-11-12-harness-haiku-openrouter-short)).

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
([rows](../benchmarks/2026-11-12-harness-haiku-short)). Only three arms can reach the model this way: Steak Pi 0.28.5,
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
are in [benchmarks/](../benchmarks). The same results are on the
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

