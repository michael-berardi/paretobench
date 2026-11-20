# review-v1

`review-v1` is the review bench's task set. It measures whether a code reviewer invents
bugs in a correct change (false alarms) and still finds the real bug in a broken change
(hits). There are 33 cases: 23 traps (`expected: clean`) and 10 controls
(`expected: bug`), in Python, JavaScript and Go.

Each `corpus/<case-id>/` directory holds:

- `diff.patch` — the change under review as a unified diff;
- `context/` — the files after the change, plus the neighbours needed to judge it. The
  reviewer sees these files and the patch, never `case.json`;
- `case.json` — the id, kind, language, expected answer, `why`, and, on controls,
  `bug_location: {path, line}` pointing at the post-change line in `context/`.

`why` explains the case to the reader. It is never shown to the reviewer. The same
neutral prompt is used for every case and arm; the verdict is the reviewer's last line,
`VERDICT: clean` or `VERDICT: bug <path>:<line>`.

## Attribution

The corpus is adapted from the `review-false-alarms` corpus in
[oh-my-hermes](https://github.com/rlaope/oh-my-hermes) at commit `bca826f`, which is
licensed under the MIT License. Their copyright line is kept verbatim in
`OMH-LICENSE` beside this file. ParetoBench's grading, runner and report are an
independent implementation in this repository's own style.

## Corrections to the source corpus

Three cases were changed after re-checking whether their `why` still held. The prompt
and the grading rules are unchanged.

- `trap-lock-held-by-caller` was mislabelled: the diff added `_total` but `reset()`
  never cleared it, so `total()` was stale after a reset. The diff and
  `context/app/metrics.py` now also add `self._total = 0` under the same lock in
  `reset()`; the hunk line numbers were regenerated. `why` says so.
- `trap-lazy-open-closed-by-exit` was mislabelled: `close()` reset `_fh` to `None`, so a
  later `write()` reopened the file in `"w"` mode and truncated the export. The diff
  and `context/app/export.py` now set a `_closed` flag in `close()` and make `write()`
  raise `ValueError("exporter is closed")` before the open path. The empty export
  still leaves no file, and `__exit__` still closes the exporter. `why` says so.
- `trap-float-equality-exact-zero` had an unstated bound: `used / limit` underflows to
  `0.0` for a huge integer `limit`, so `ratio == 0.0` could mislabel a nonzero `used`
  as unused. `context/app/plans.py` now shows the only caller, which validates the
  quota to at most 2,000,000,000 from a 32-bit column, and `why` names that bound.
  The diff itself is unchanged.

Every other trap was re-checked against its `why` and its neighbours in `context/`.
The traps whose safety depends on a caller (the locked caller, the sorted store, the
validated retry policy, the decoder's type tag, the startup initialiser, the validated
menu depth and the init-only map) keep that evidence in `context/`; the objections they
attract in reviewer output are about hypothetical callers or exported helpers, not
about a bug reachable through the code shipped in the case. In particular,
`trap-go-shift-bounded-by-policy` was kept: `Delay`'s only caller is `Do`, whose
`attempt` is below `p.maxAttempts`, and `NewPolicy` refuses `MaxAttempts > 8` and
`Base > 5s`; fields are unexported, so neither a shift overflow nor a negative
attempt is reachable.

`fixtures/recorded-verdicts.json` holds hand-written replies for the offline dry run.
It exercises every grading path; its numbers measure nothing.
