# ParetoBench methodology

This document says what the benchmark measures, how it measures it, and what the numbers do not mean.

## The two benches

ParetoBench Harness answers one question: with the same model, which coding-agent harness gets the task done
correctly for the least cost and time? It runs one model across several harnesses. Comparisons are only ever
made within one model. A model lists the harnesses that can run it.

ParetoBench Model answers the other question: under one harness, with identical tools, prompts and effort
policy, which model gets the task done correctly for the least cost and time? The default harness is steak-pi.

The name is literal. Every report marks the Pareto frontier. An entry is on the frontier when no other entry
is at least as correct and at least as cheap, with one strictly better. There is a second frontier for correct
rate against time. An entry with no correct run is never on a frontier.

## The task set

There are 20 small Python tasks. Each task is one prompt and one deterministic hidden checker. The agent never
sees the checker. A task is admitted only when all of these hold:

1. The checker is deterministic. It runs scripts and compares files and answers. It does not ask a model.
2. Every requirement is stated in the prompt. The checker may not demand anything the prompt did not say.
3. A reference solution exists in `tasks/reference/` and passes the checker on a fresh fixture.
4. The selftest passes: the checker fails on the untouched fixture and passes after the reference solution.
   For tasks where an obvious wrong fix exists, the checker must also fail after that wrong fix.
5. The task discriminates. It belongs to one of the eight categories below.

The eight discrimination categories, with the current tasks:

1. Trivial task overhead. One small edit, so harness overhead is visible. (t3)
2. Precise scoped edits. Change exactly what is asked and nothing else, down to bytes. (t2, h9)
3. Bug fixes from symptoms or partial tests. The visible tests do not cover the whole rule. (t1, t8, h1, h2)
4. Fixes where the obvious wrong fix must fail. The checker rejects the shallow patch. (h3, h4)
5. Refactors with exceptions. Rename across files, keep behaviour, keep named literals. (t4, h8)
6. New code to a stated spec. Add a function, a script or a feature and verify it. (t5, t7, h10)
7. Read-only questions over large files. Answer from the data, modify nothing. (t6, h5, h6, h11)
8. Multi-step instructions and search. Several steps with constraints, or one needle in many files. (h7, h12)

The fixture is copied fresh for every run. Two large files are generated with fixed seeds, so every run sees
identical inputs. The task set is hashed: `tasks.json`, the checks, the fixture and the generator. Every row
carries that hash as `task_set`. The report refuses to mix rows from different task sets.

## Controls

Both benches hold everything fixed except the thing being compared.

- Same model and same effort within a comparison. The model config sets the effort once.
- Same prompt text for every entry. Same checker. Same fresh fixture per run.
- Stock config per harness. No harness gets tuning that the others do not get.
- Exact commands per harness. They are listed below and built by the adapters in `paretobench/harnesses/`.
- One throwaway warm-up request per lane before the measured runs. This keeps the cache-write charge for the
  starting prompt out of the comparison. An arm whose every warm-up fails aborts with a named error.
- Balanced order. For each (rep, task) the entry order rotates, so no entry always runs first or last.
- Hard timeout per run (default 600 s). The whole child process group is killed.
- Failures, timeouts and harness errors stay in the sample as incorrect runs. They are never dropped.
- A provider that refuses the request is a harness failure with the provider's own message, even when the
  harness exits 0. It is never recorded as a silent zero-token wrong answer.

Exact commands (prompt last, cwd is the fresh fixture):

- pi: `<PB_PI_BIN> -p --mode json --no-session -ne <model args> <prompt>`. The agent dir has copies of
  auth.json and models.json and a settings.json with no packages.
- steak-pi: `<PB_PI_BIN> -p --mode json --no-session <model args> <prompt>`. Same agent dir, but
  settings.json lists the Steak Pi package. Optional steak-pi-only flags come from `steak_pi_extra`.
- claude-code: `<PB_CLAUDE_BIN> -p <model args> --no-session-persistence --setting-sources ""
  --disable-slash-commands --strict-mcp-config --no-chrome --permission-mode acceptEdits
  --allowedTools Bash,Read,Edit,Write,Glob,Grep --output-format json <prompt>`.
- dsh: `<PB_DSH_BIN> headless --patch <generated model patch> --json --permission-mode workspace-write
  --approval-policy never <prompt>`. Per-lane DSH_HOME, telemetry disabled.
- steak-dsh: the dsh command plus `--patch <PB_STEAK_DSH_PATCH>` after the model patch.

Keys are read from the Pi agent auth store at run time. They go only into the child environment. They are
never printed, never stored in rows, never passed on a command line, and scrubbed from raw logs.

## What is recorded

One JSON row per run: bench, harness, model, task, rep, correct, wall seconds, uncached input tokens,
cache-read and cache-write tokens, output tokens, reasoning tokens, turns, tool calls, retries, error text,
checker error text, harness version, pb version, task set hash, and a timestamp. Raw event streams can be
kept with `PB_LOG_DIR`, with keys scrubbed. Rows are appended one at a time. An interrupted run resumes:
rows already present for (harness, model, task, rep) are skipped.

## Cost

Cost is computed by the report from one rate table per model, applied to every harness. It never comes from
a harness's own accounting. In the model bench each model has its own price. Dollars are compared only when
every model has one. When any model is on a flat plan, every model is compared in weighted tokens and the
list-price dollars are shown beside each priced model. When every rate for a model is zero (a flat plan), the report uses weighted
tokens instead of dollars: input 1, cacheRead 0.1, cacheWrite 1.25, output 4. The column is labelled as
weighted tokens. Weighted tokens are a proxy, not a price.

## Statistics

Per entry: correct out of total with a Wilson 95% interval, total cost, cost per correct run, token totals,
median and p90 wall seconds, median turns.

Comparisons are paired on (task, rep). Pairing removes the task mix and the repeat-to-repeat noise, which
are large compared with the differences between entries. For each measure (cost, total input, output, wall
time) the report gives the ratio of totals with a 95% bootstrap interval: 5000 resamples, seed 1, resampling
whole (task, rep) pairs. It also counts the pairs the entry won on cost.

Correctness differences use the exact paired sign test (McNemar exact, two-sided) on the discordant pairs.
With few repeats the intervals are wide. That is honest: few repeats cannot settle small effects.

The verdict rule, in plain words:

- "better" only when correct is not lower and the cost interval is wholly below 1.00.
- "worse" when the cost interval is wholly above 1.00, or correct is lower with p < 0.05.
- otherwise "no clear difference".

## Gates

Write the gate before running. A gate says what result would count as better, before any numbers exist.
Record any change to the gate before the extra runs that use it, and say why. Do not move the gate after
seeing the numbers. The steak-dsh project's GATE.md is an example of this practice, including a recorded
amendment after a first look.

## Limits

- 20 small Python tasks. They measure harness overhead and reliability on short tasks, not large-repo skill.
- One machine. Wall time is noisy, especially under parallel runs. Treat time as indicative.
- Flat-plan models have no dollar price. Their comparisons use weighted tokens, a proxy.
- A harness can only be compared on models it can run. Claude Code runs Claude models only.
- Results age as harnesses and models change. Every row carries versions and dates for this reason.
- The dsh family reaches non-native models through declared gateway routes. Cache behaviour differs from a
  native route. This affects all dsh-family entries equally, but not the pi family or claude-code.

## Adding things

Add a harness adapter: create `paretobench/harnesses/<name>.py` with the adapter interface (validate,
version, setup_lane, build_command, parse, after_run), register it in `harnesses/__init__.py`, add command
construction tests with fake executables, and document the exact command here. The adapter must never see
a key.

Add a model: add an entry to your models config with a `harnesses` list, per-harness settings and one rate
table. Run `paretobench validate` and `paretobench doctor --model KEY`.

Add a task: write the prompt with every requirement stated, write the hidden checker, write the reference
solution, and make the selftest pass. Put it in a category or argue for a new one. A changed task set gets
a new hash and starts a new results series. Never edit a task set under published results.

## Versioning

Every row carries `task_set` (the hash of the task files) and `pb_version`. A changed task set starts a new
results series. The report refuses to mix task sets. Legacy steak-dsh rows without a hash are treated as
the set `legacy-steak-dsh-bench`, and a results dir may hold that one legacy set.
