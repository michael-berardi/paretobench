# long-v1 pilot, 2026-11-12

Admission rule 6 (docs/METHODOLOGY.md): every arm, two repeats; a task that every arm passes on every repeat, or every
arm fails on every repeat, is dropped.

Run: arms `dsh`, `steak-dsh`, `steak-dsh-long`, `steak-pi`, `pi`; one Flash-class model on a per-token route;
2 repeats; 110 runs; no timeouts.

The rows carry a model key, so they live with the other dated results, in `benchmarks/2026-11-12-long-v1-pilot-*/`:

- `rows.jsonl`: the pilot, all eleven tasks, 110 rows, set hash `b9348b7c3c551ad3`.
- `rows-L8-corrected-prompt.jsonl`: L8 again after its prompt was corrected, 10 rows, set hash `669740c30d0f28b8`.

## Outcome

| task | result | decision |
|---|---|---|
| L1 to L7, L9, L10, L11 | every arm passed both repeats | dropped: does not discriminate on this model |
| L8, first run | 2 passes in 10 | not counted: the prompt was wrong (below) |
| L8, corrected prompt | every arm passed both repeats | dropped: does not discriminate on this model |

No task is admitted on this model. The long gate was not run, and no long-set result is published.

## The L8 defect

The prompt asked `log-windows` to print `{"requests": <parsed entries>, ...}`. The hidden test and the reference
expect the number of parsed entries. Eight of ten runs printed the entries themselves, which is a fair reading of the
prompt, so the checker demanded something the prompt did not say (rule 2). The prompt now says
`<number of parsed entries>`. This changes the set hash from `b9348b7c3c551ad3` to `669740c30d0f28b8`.

## What this means

The eleven tasks are sound as tasks (references pass, untouched fixtures fail, wrong fixes fail) but too easy to
separate these harnesses on this model: a long task that every harness completes says nothing about which harness is
better at long work. Cost did differ between arms in the pilot rows, but the pilot is two repeats and was not a
pre-registered comparison, so no verdict is drawn from it. A harder set, or a pilot on a weaker model, is needed before
the long gate can run.
