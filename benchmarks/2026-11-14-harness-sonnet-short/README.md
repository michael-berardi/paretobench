# Five harnesses on Claude Sonnet 5.5, short set, 2026-11-14

Answer first: on this set every harness got every task right, so correctness does not separate them. Steak Pi was the
cheapest. Codex CLI was the fastest by median time. Claude Code was the most expensive and not faster.

## What was run

- Model: Claude Sonnet 5.5, reasoning effort medium, on a Claude Code subscription login. All five arms use that
  same login.
- Task set `3c3185f48a7f97a0` (the short set, 20 tasks), three repetitions each: 5 arms x 20 tasks x 3 = 300 runs.
  The rows were produced by the code that became ParetoBench 0.5.0; they carry `pb_version` 0.4.2 because the version
  bump came after the run. Each arm runs in a fresh fixture, paired on task and repetition.
- Arms and versions as reported by the tools: Claude Code 2.1.325; Codex CLI 0.153.0; Steak Pi 0.29.0 (`steak-pi`
  and `steak-pi-lean`, the latter as `steak-pi run --lean`); Steak DSH build `0.2.2-rc.1`.
- How Codex CLI was run: stock Codex CLI, through a local bridge that sends its model requests onto the same
  subscription login the other arms use. Codex keeps its own prompts, tools and sandbox. The bridge is not
  published, so the Codex row cannot be reproduced from this repository alone. ParetoBench needs a bridge you supply
  (`PB_CODEX_BRIDGE`, see `docs/METHODOLOGY.md`). Codex reports usage per turn, so its turn count is a lower bound.
- The Codex rows were produced after the accounting fix released in 0.5.0: cache writes are no longer also counted as uncached
  input.
- Cost is the model's list price per token applied to the token counts (`rates` in the models file). On a
  subscription nothing was charged per token, so cost is an estimate for comparison, not a bill.

## Results

300 of 300 runs correct. Cost is list price per run, averaged over 60 runs. Time is seconds per run. Ratios are
paired on (task, repetition) against Claude Code, with 95% bootstrap intervals (5000 resamples, seed 1). Below 1.00
is cheaper or faster.

| Harness | Correct | Cost per run | Median time | p90 time | Cost vs Claude Code (95%) | Time vs Claude Code (95%) |
|---|---|---|---|---|---|---|
| Claude Code | 60/60 | $0.0202 | 9.4 s | 13.6 s | 1.00 | 1.00 |
| Codex CLI | 60/60 | $0.0139 | 8.4 s | 11.9 s | 0.69 (0.64 to 0.74) | 0.89 (0.83 to 0.95) |
| Steak DSH | 60/60 | $0.0128 | 10.1 s | 16.5 s | 0.63 (0.57 to 0.71) | 1.11 (1.05 to 1.18) |
| Steak Pi | 60/60 | $0.0097 | 9.1 s | 14.1 s | 0.48 (0.44 to 0.52) | 0.96 (0.89 to 1.03) |
| Steak Pi, lean | 60/60 | $0.0098 | 9.1 s | 13.5 s | 0.49 (0.45 to 0.53) | 0.95 (0.88 to 1.02) |

Full tables, token counts, per-task results and frontiers: `summary.md` and `summary.json`. Raw rows: `rows.jsonl`.

## What works best with this model

- Correctness: no arm is better. All five solved all 60 of their runs. The 95% Wilson interval for 60 of 60 is 0.94
  to 1.00 for every arm.
- Cost: Steak Pi, default or lean, was cheapest at about $0.0097 per run, 0.48 times Claude Code's cost (0.44 to
  0.52). Steak DSH was 0.63 times (0.57 to 0.71) and Codex CLI 0.69 times (0.64 to 0.74). Steak Pi was cheaper than
  Claude Code in 60 of 60 pairs. Lean and default Steak Pi did not differ.
- Time: Codex CLI had the lowest median, 8.4 s, and was 0.89 times Claude Code's time (0.83 to 0.95). Steak Pi was
  level with Claude Code (0.96, 0.89 to 1.03). Steak DSH was slower, 1.11 times (1.05 to 1.18).
- Together: Steak Pi had the lowest cost with time level with Claude Code; Codex CLI had the lowest time at higher
  cost than Steak Pi. Claude Code was most expensive and not faster than Codex CLI.

## Limits

- One model, one machine, one day. Time depends on the subscription route's load and can differ across runs.
- The short set is at ceiling: 300 of 300 correct. It says nothing about which arm solves harder problems.
- Three repetitions per task. The intervals resample 60 pairs and are wide enough that small gaps (for example
  Steak Pi against Claude Code on time) are not separated.
- List-price cost on a subscription login is an estimate, not a charge. The ranking follows token counts, mainly how
  much input each arm reads from cache and writes to it.
- The Codex row ran through an unpublished bridge, which adds its own translation of requests and token counts. Read
  its numbers as measured through that bridge, not as stock Codex CLI on a native route.
- Two arms were not run: stock Pi and stock DeepSeek Harness. Neither can run on a subscription route, and no
  approved per-token route serves this model.
