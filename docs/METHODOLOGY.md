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
6. For a long task set (below), a pilot decides: a task that every arm passes on every repeat, or every arm fails
   on every repeat, is dropped before the set is hashed. Record the pilot rows with the set.

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

## The long task set (long-v1)

The 20 short tasks cannot say which harness is better at the work the operator actually does: long, multi-step
sessions on a real-sized repository, read-only scouting, test writing, delegated waves, work that outlives one
context window. `long-v1` is a second task set for that. It lives in `tasks-long/`, has its own `tasks.json`,
generator, hidden checkers and reference solutions, and is selected with `--task-set long-v1`. The short set, its
files and its hash (`3c3185f48a7f97a0`) are untouched; rows of the two sets are never mixed in one report.

Fixture. `gen_fixture.py` builds one deterministic, seeded multi-package Python repository (about 9,400 lines in 7
packages: `core`, `store`, `api`, `cli`, `ingest`, `plugins`, `tests`) with a stdlib `unittest` suite that is green on
the clean base, a 2 MB access log, a CSV and a JSONL file, 60 plugin modules and 24 entity models (many of them
decoys for any given task). The generator is called as `prepare(dest, task)`: after the base is written, a per-task
setup plants only what that task needs (a bug, decoys, deprecated calls, a ledger report). Two generations with the
same seed are byte-identical (`pb selftest --task-set long-v1` and `tests/test_long_set.py` prove it).

Checkers. Each task has a hidden deterministic checker (`tasks-long/checks/check.py`, hidden tests in
`checks/hidden/`). The checker lives outside the fixture and never runs inside the agent's tree: it copies the tree to
a scratch folder, overlays the hidden tests there, and regenerates the pristine tree from the seed to compare
against. Where a task may change only some files, every other file in the tree must be byte-identical to the
pristine one (a full-tree SHA manifest; `__pycache__`, `ans.txt` and dot-directories left by a harness are ignored).
Read-only tasks (L4) allow no change at all. A checker that finds a missing file or an unparsable file fails the
run with the reason on stderr; the reason goes into the row's `chk_err`.

Tasks (class mirrored from the operator's real workload, what it discriminates, how it is judged):

| id | task | judged by |
|---|---|---|
| L1 | multi-file feature: cursor pagination across `store`, `api`, `cli`, docs and tests | hidden feature tests, the full suite, a docs section, only the named files changed |
| L2 | bug hunt: one failing test, root cause three calls deep, decoys | the failing test and the whole suite pass, hidden boundary tests, one file changed, at most 4 changed lines |
| L3 | refactor: one SKU normaliser copied into four packages becomes one in `core` | suite, hidden behaviour tests (error messages included), AST check that the logic exists once, a deliberately different look-alike untouched |
| L4 | read-only scouting: five exact answers (definition site, a constant, every call site as file:line, two numbers computed from the 2 MB log) | exact match; any change to the tree fails |
| L5 | test writing for `core.pricing`, source frozen | tests pass on clean code and must kill at least 10 of 12 deterministic mutants; no source inspection allowed |
| L6 | compaction stress: five facts from a 3 MB report early on, delete it, migrate a deprecated call in 40 files, answer at the end | AST equality of every Python file with the expected migration, report deleted, the five facts exact, suite passes |
| L7 | hard codegen: retry with backoff, a token-bucket limiter, two CLI utilities | seeded property tests against an independent model, CLI integration |
| L8 | delegated wave: three independent package changes plus an integration step | per-package hidden tests, CLI integration tests, suite, only the named files changed |
| L9 | batch of 12 exact one-line edits | every file equals the expected text; everything else byte-identical |
| L10 | tool-loop recovery: the check command fails twice with a misleading message before it tells the truth | suite, hidden tests, the check command must have ended green, one file changed |
| L11 | finish-guard trap: five parts, the last one (regenerate a golden file) looks blocked on a missing token and is not | all five parts verified in the tree |

Step calibration. Every reference solution is a script written in tool-step primitives (`tasks-long/reference/_ref.py`:
read, search, edit, write, run a command, list a folder). Its step count is printed and must lie between 10 and 40
(L6, the compaction task, more than 40); the count is recorded in `tasks-long/steps.json` and the selftest fails if the
reference and the record disagree. The count is a calibration of how much work the task needs, not a score.

What the checker cannot see, the logs can. A checker only sees the final tree. Delegation use (L8), compaction or
context-edit counts (L6) and tool-error counts (L10) have to be read from the raw event streams, so run the long set
with `PB_LOG_DIR` set (see the gates below). The row's `turns` and `tools` are always recorded.

Per-task wall budget. When `--timeout` is not given the hard timeout comes from `tasks-long/budgets.json`: 1800 s per
run, 3600 s for L6. A run that hits it stays in the sample as incorrect and is counted under `timeouts` in the report.

Admission. A task enters `long-v1` only when rules 1 to 5 above hold, its reference passes and its untouched fixture
fails, and rule 6 holds: a pilot (every arm, two repeats) drops any task that every arm passes on every repeat or
every arm fails on every repeat. Dropped tasks are listed with the pilot rows in `tasks-long/pilot/`, and only then is the
set hashed and published. Status of this draft: the eleven tasks are built and selftested; the pilot has not run, so
the hash printed by `pb validate` is provisional and no result may be published under it until the pilot is done.

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
- steak-pi-lean: the steak-pi command with `--exclude-tools ultraterm_subagents,todo` inserted before the prompt
  (the dispatch and todo tools off). Everything else, including the agent dir and package, is the steak-pi arm.
- steak-dsh-long: the steak-dsh command plus `--patch <long.patch.yml>` after the bundle patch, where
  `long.patch.yml` is looked up beside `PB_STEAK_DSH_PATCH`. A bundle without it stops the run before anything
  starts with the named error `steak-dsh-long-patch-missing`.

The model entry must list the new arm names under `harnesses` before they can run.

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
median and p90 wall seconds, median turns. Three reliability measures are printed beside them: pass@k (the share of
tasks with at least one correct repeat), pass^k (the share with every repeat correct), the number of runs that ended at
the hard timeout, and the correct rate of each repeat, which shows drift between repeats (a provider or cache change
during a long run) that the pooled correct count hides.

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

### Gates written before the runs

These are written before any run that uses them and are not moved after the numbers exist (see above).

Lean gate. Question: does switching off the dispatch and todo tools remove the short-task overhead of Steak Pi?
Run: `pi`, `steak-pi`, `steak-pi-lean`, short set, one model, 3 repeats, `PB_LOG_DIR` set. `steak-pi-lean` is kept as
an arm only if the report's verdict for it against `steak-pi` is "better" (correct not lower, cost interval wholly
below 1.00). Its gap to stock `pi` is reported without a pass or fail. If the verdict is "no clear difference" the
lean arm is dropped from the published tables and the result is stated as such.

Long gate. Question: on long work, does the long-work Steak DSH profile beat stock DSH, and where do the Steak Pi and
stock Pi arms stand? Run: `dsh`, `steak-dsh`, `steak-dsh-long`, `steak-pi`, `pi`, set `long-v1` (after its pilot),
one model per comparison, 5 repeats, `PB_LOG_DIR` set, the budgets in `budgets.json`. `steak-dsh-long` passes only if all of these hold against `dsh`: (1) correct
not lower; (2) the cost interval is wholly below 1.00 ("better"); (3) there is no task on which `steak-dsh-long` fails every
repeat while `dsh` passes every repeat; (4) it has no more timeouts than `dsh`. The same three conditions are read for `steak-dsh`, which
shows whether the profile is what moved the result. `steak-pi` and `pi` are reported as references and judged by
the same verdict rule against `dsh`, not gated.

Any change to a gate is recorded here with its reason before the runs that use it.

## Limits

- 20 small Python tasks. They measure harness overhead and reliability on short tasks, not large-repo skill. The long
  set (`long-v1`) covers that, but it is one generated repository, not a real one, and its hidden checkers see only the
  final tree. It is unpiloted until its pilot has run.
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
