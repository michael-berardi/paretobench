ParetoBench harness bench, task set 3c3185f48a7f97a0, 180 rows

ParetoBench **harness** bench. Task set `3c3185f48a7f97a0`, 180 rows, pb 0.3.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek (per-token prices of the route; DSH cannot send the gateway's session-affinity headers on a declared route, Steak Pi does)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pi | 60/60 | 0.94-1.00 | 123,181 | 959,232/0 | 60,842 | 0.0395 | 0.0007 | 0.0395 | 7.1 | 13.0 | 4.5 | yes | yes |
| steak-pi | 60/60 | 0.94-1.00 | 143,006 | 5,949,440/0 | 112,380 | 0.0909 | 0.0015 | 0.0909 | 11.6 | 21.2 | 5.5 | no | no |
| steak-pi-lean | 60/60 | 0.94-1.00 | 107,346 | 1,131,264/0 | 65,626 | 0.0422 | 0.0007 | 0.0422 | 8.9 | 18.7 | 5.0 | no | no |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi-lean | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |

pi vs steak-pi, paired on 60 (task, rep) pairs; pi cheaper in 59/60 pairs; correct 60 vs 60

| measure | pi/steak-pi | 95% CI |
|---|---|---|
| cost $ | 0.43 | 0.36-0.52 |
| total_input | 0.18 | 0.15-0.21 |
| output | 0.54 | 0.43-0.67 |
| wall_time | 0.58 | 0.49-0.67 |

Verdict: **better**.

steak-pi-lean vs steak-pi, paired on 60 (task, rep) pairs; steak-pi-lean cheaper in 56/60 pairs; correct 60 vs 60

| measure | steak-pi-lean/steak-pi | 95% CI |
|---|---|---|
| cost $ | 0.46 | 0.36-0.63 |
| total_input | 0.20 | 0.17-0.25 |
| output | 0.58 | 0.43-0.87 |
| wall_time | 0.70 | 0.55-0.90 |

Verdict: **better**.

| task | pi | steak-pi | steak-pi-lean |
|---|---|---|---|
| h1 | 3/3 | 3/3 | 3/3 |
| h10 | 3/3 | 3/3 | 3/3 |
| h11 | 3/3 | 3/3 | 3/3 |
| h12 | 3/3 | 3/3 | 3/3 |
| h2 | 3/3 | 3/3 | 3/3 |
| h3 | 3/3 | 3/3 | 3/3 |
| h4 | 3/3 | 3/3 | 3/3 |
| h5 | 3/3 | 3/3 | 3/3 |
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

