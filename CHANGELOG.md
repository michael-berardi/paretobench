# Changelog

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
