# Published results

One folder per dated run, for example `2026-11-11-qwen-harness/`. Each folder holds the raw rows
(`rows.jsonl`, or the imported legacy file) plus `summary.json` and `summary.md` written by
`paretobench report`.

Every row carries `task_set`, `pb_version`, `harness_version` and a timestamp, so results from different
task sets or versions are never mixed. Rows without a task-set hash are the legacy steak-dsh set
(`legacy-steak-dsh-bench`).

Do not edit published rows. A changed task set starts a new series in a new folder.
