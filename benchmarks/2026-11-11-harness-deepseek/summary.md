ParetoBench harness bench, task set 3c3185f48a7f97a0, 240 rows

ParetoBench **harness** bench. Task set `3c3185f48a7f97a0`, 240 rows, pb 0.1.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek (per-token prices of the route; DSH cannot send the gateway's session-affinity headers on a declared route, Steak Pi does)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dsh | 60/60 | 0.94-1.00 | 343,219 | 2,127,872/0 | 69,179 | 0.0572 | 0.0010 | 0.0572 | 20.4 | 40.0 | 5.0 | no | no |
| pi | 60/60 | 0.94-1.00 | 261,205 | 690,944/0 | 46,967 | 0.0361 | 0.0006 | 0.0361 | 14.8 | 28.5 | 4.5 | yes | yes |
| steak-dsh | 60/60 | 0.94-1.00 | 300,507 | 1,341,184/0 | 71,379 | 0.0529 | 0.0009 | 0.0529 | 21.3 | 41.3 | 5.0 | no | no |
| steak-pi | 60/60 | 0.94-1.00 | 371,060 | 2,933,248/0 | 91,555 | 0.0734 | 0.0012 | 0.0734 | 22.5 | 45.1 | 5.0 | no | no |

dsh vs pi, paired on 60 (task, rep) pairs; dsh cheaper in 8/60 pairs; correct 60 vs 60

| measure | dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.59 | 1.44-1.74 |
| total_input | 2.60 | 2.24-2.96 |
| output | 1.47 | 1.33-1.63 |
| wall_time | 1.41 | 1.27-1.57 |

Verdict: **worse**.

steak-dsh vs pi, paired on 60 (task, rep) pairs; steak-dsh cheaper in 18/60 pairs; correct 60 vs 60

| measure | steak-dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.47 | 1.26-1.70 |
| total_input | 1.72 | 1.44-2.01 |
| output | 1.52 | 1.26-1.81 |
| wall_time | 1.44 | 1.28-1.60 |

Verdict: **worse**.

steak-pi vs pi, paired on 60 (task, rep) pairs; steak-pi cheaper in 4/60 pairs; correct 60 vs 60

| measure | steak-pi/pi | 95% CI |
|---|---|---|
| cost $ | 2.04 | 1.71-2.37 |
| total_input | 3.47 | 2.73-4.30 |
| output | 1.95 | 1.62-2.28 |
| wall_time | 1.63 | 1.41-1.87 |

Verdict: **worse**.

| task | dsh | pi | steak-dsh | steak-pi |
|---|---|---|---|---|
| h1 | 3/3 | 3/3 | 3/3 | 3/3 |
| h10 | 3/3 | 3/3 | 3/3 | 3/3 |
| h11 | 3/3 | 3/3 | 3/3 | 3/3 |
| h12 | 3/3 | 3/3 | 3/3 | 3/3 |
| h2 | 3/3 | 3/3 | 3/3 | 3/3 |
| h3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h4 | 3/3 | 3/3 | 3/3 | 3/3 |
| h5 | 3/3 | 3/3 | 3/3 | 3/3 |
| h6 | 3/3 | 3/3 | 3/3 | 3/3 |
| h7 | 3/3 | 3/3 | 3/3 | 3/3 |
| h8 | 3/3 | 3/3 | 3/3 | 3/3 |
| h9 | 3/3 | 3/3 | 3/3 | 3/3 |
| t1 | 3/3 | 3/3 | 3/3 | 3/3 |
| t2 | 3/3 | 3/3 | 3/3 | 3/3 |
| t3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t4 | 3/3 | 3/3 | 3/3 | 3/3 |
| t5 | 3/3 | 3/3 | 3/3 | 3/3 |
| t6 | 3/3 | 3/3 | 3/3 | 3/3 |
| t7 | 3/3 | 3/3 | 3/3 | 3/3 |
| t8 | 3/3 | 3/3 | 3/3 | 3/3 |

