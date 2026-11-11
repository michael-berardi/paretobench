ParetoBench harness bench, task set 3c3185f48a7f97a0, 80 rows

ParetoBench **harness** bench. Task set `3c3185f48a7f97a0`, 80 rows, pb 0.1.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model haiku (Claude subscription model. Stock pi has no route to it; the steak-pi arm reaches it through Steak Pi's own provider.)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code | 39/40 | 0.87-1.00 | 342 | 4,136,260/186,631 | 74,974 | 0.1162 | 0.0030 | 0.1162 | 11.4 | 22.0 | 5.0 | no | yes |
| steak-pi | 40/40 | 0.91-1.00 | 378 | 1,870,578/250,097 | 48,772 | 0.0931 | 0.0023 | 0.0931 | 19.4 | 36.1 | 5.0 | yes | yes |

steak-pi vs claude-code, paired on 40 (task, rep) pairs; steak-pi cheaper in 35/40 pairs; correct 40 vs 39, exact sign test p=1.0000

| measure | steak-pi/claude-code | 95% CI |
|---|---|---|
| cost $ | 0.80 | 0.56-1.17 |
| total_input | 0.49 | 0.42-0.56 |
| output | 0.65 | 0.56-0.76 |
| wall_time | 1.52 | 1.37-1.68 |

Verdict: **no clear difference**.

| task | claude-code | steak-pi |
|---|---|---|
| h1 | 2/2 | 2/2 |
| h10 | 2/2 | 2/2 |
| h11 | 2/2 | 2/2 |
| h12 | 2/2 | 2/2 |
| h2 | 2/2 | 2/2 |
| h3 | 2/2 | 2/2 |
| h4 | 2/2 | 2/2 |
| h5 | 2/2 | 2/2 |
| h6 | 2/2 | 2/2 |
| h7 | 1/2 | 2/2 |
| h8 | 2/2 | 2/2 |
| h9 | 2/2 | 2/2 |
| t1 | 2/2 | 2/2 |
| t2 | 2/2 | 2/2 |
| t3 | 2/2 | 2/2 |
| t4 | 2/2 | 2/2 |
| t5 | 2/2 | 2/2 |
| t6 | 2/2 | 2/2 |
| t7 | 2/2 | 2/2 |
| t8 | 2/2 | 2/2 |

