ParetoBench harness bench, task set 3c3185f48a7f97a0, 180 rows

ParetoBench **harness** bench. Task set `3c3185f48a7f97a0`, 180 rows, pb 0.4.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model haiku (Claude subscription model. Stock pi has no route to it; the steak-pi arm reaches it through Steak Pi's own provider.)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code | 60/60 | 0.94-1.00 | 518 | 6,385,526/279,873 | 112,217 | 0.1760 | 0.0029 | 0.1760 | 8.4 | 18.6 | 5.0 | no | yes |
| steak-pi | 60/60 | 0.94-1.00 | 510 | 2,257,932/202,233 | 66,412 | 0.0963 | 0.0016 | 0.0963 | 9.7 | 19.8 | 4.0 | yes | no |
| steak-pi-lean | 58/60 | 0.89-0.99 | 504 | 1,093,454/217,128 | 67,709 | 0.0883 | 0.0015 | 0.0883 | 9.4 | 19.1 | 4.0 | yes | no |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| claude-code | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi-lean | 1.00 (k=3) | 0.95 | 0 | r0=1.00 r1=0.95 r2=0.95 |

steak-pi vs claude-code, paired on 60 (task, rep) pairs; steak-pi cheaper in 58/60 pairs; correct 60 vs 60

| measure | steak-pi/claude-code | 95% CI |
|---|---|---|
| cost $ | 0.55 | 0.49-0.60 |
| total_input | 0.37 | 0.34-0.41 |
| output | 0.59 | 0.52-0.66 |
| wall_time | 1.06 | 0.98-1.14 |

Verdict: **better**.

steak-pi-lean vs claude-code, paired on 60 (task, rep) pairs; steak-pi-lean cheaper in 59/60 pairs; correct 58 vs 60, exact sign test p=0.5000

| measure | steak-pi-lean/claude-code | 95% CI |
|---|---|---|
| cost $ | 0.50 | 0.43-0.57 |
| total_input | 0.20 | 0.17-0.23 |
| output | 0.60 | 0.52-0.69 |
| wall_time | 1.00 | 0.91-1.09 |

Verdict: **no clear difference**.

| task | claude-code | steak-pi | steak-pi-lean |
|---|---|---|---|
| h1 | 3/3 | 3/3 | 3/3 |
| h10 | 3/3 | 3/3 | 3/3 |
| h11 | 3/3 | 3/3 | 3/3 |
| h12 | 3/3 | 3/3 | 3/3 |
| h2 | 3/3 | 3/3 | 3/3 |
| h3 | 3/3 | 3/3 | 3/3 |
| h4 | 3/3 | 3/3 | 3/3 |
| h5 | 3/3 | 3/3 | 1/3 |
| h6 | 3/3 | 3/3 | 3/3 |
| h7 | 3/3 | 3/3 | 3/3 |
| h8 | 3/3 | 3/3 | 3/3 |
| h9 | 3/3 | 3/3 | 3/3 |
| t1 | 3/3 | 3/3 | 3/3 |
| t2 | 3/3 | 3/3 | 3/3 |
| t3 | 3/3 | 3/3 | 3/3 |
| t4 | 3/3 | 3/3 | 3/3 |
| t5 | 3/3 | 3/3 | 3/3 |
| t6 | 3/3 | 3/3 | 3/3 |
| t7 | 3/3 | 3/3 | 3/3 |
| t8 | 3/3 | 3/3 | 3/3 |

