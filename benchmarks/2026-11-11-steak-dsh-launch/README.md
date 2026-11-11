# 2026-11-11 steak-dsh launch results (imported legacy rows)

Raw per-run rows imported from the steak-dsh bench's final published results, one file per model:
deepseek v4.1 flash (dsh, steak-dsh, steak-pi), qwen4 max (dsh, steak-dsh, steak-pi), and
haiku 5.5 (steak-pi vs claude-code). These rows predate ParetoBench: they carry the old arm names
(`dsh`, `sdsh`, `sp`, `cc`) and no task-set hash, so they are reported as the legacy set
`legacy-steak-dsh-bench`. `summary.json` and `summary.md` were produced by `paretobench report` on
this folder; different models in one folder are reported per model.
