ParetoBench harness bench, task set 3c3185f48a7f97a0, 300 rows

ParetoBench **harness** bench. Task set `3c3185f48a7f97a0`, 300 rows, pb 0.4.1. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek (per-token prices of the route; DSH cannot send the gateway's session-affinity headers on a declared route, Steak Pi does)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codex | 60/60 | 0.94-1.00 | 344,180 | 3,165,568/0 | 88,031 | 0.0719 | 0.0012 | 0.0719 | 28.8 | 69.8 | 5.0 | no | no |
| dsh | 60/60 | 0.94-1.00 | 302,023 | 2,117,376/0 | 62,630 | 0.0525 | 0.0009 | 0.0525 | 22.9 | 65.1 | 5.0 | no | no |
| pi | 60/60 | 0.94-1.00 | 214,703 | 647,552/0 | 42,648 | 0.0321 | 0.0005 | 0.0321 | 19.4 | 38.4 | 4.0 | yes | yes |
| steak-dsh | 60/60 | 0.94-1.00 | 209,510 | 1,049,728/0 | 42,338 | 0.0338 | 0.0006 | 0.0338 | 20.6 | 51.3 | 4.0 | no | no |
| steak-pi | 60/60 | 0.94-1.00 | 206,627 | 831,360/0 | 43,893 | 0.0333 | 0.0006 | 0.0333 | 22.3 | 53.5 | 5.0 | no | no |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| codex | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |

codex vs pi, paired on 60 (task, rep) pairs; codex cheaper in 6/60 pairs; correct 60 vs 60

| measure | codex/pi | 95% CI |
|---|---|---|
| cost $ | 2.24 | 1.88-2.62 |
| total_input | 4.07 | 3.61-4.54 |
| output | 2.06 | 1.61-2.57 |
| wall_time | 1.58 | 1.28-1.94 |

Verdict: **worse**.

dsh vs pi, paired on 60 (task, rep) pairs; dsh cheaper in 4/60 pairs; correct 60 vs 60

| measure | dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.64 | 1.46-1.82 |
| total_input | 2.81 | 2.55-3.10 |
| output | 1.47 | 1.30-1.66 |
| wall_time | 1.37 | 1.06-1.73 |

Verdict: **worse**.

steak-dsh vs pi, paired on 60 (task, rep) pairs; steak-dsh cheaper in 28/60 pairs; correct 60 vs 60

| measure | steak-dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.05 | 0.95-1.18 |
| total_input | 1.46 | 1.35-1.58 |
| output | 0.99 | 0.89-1.12 |
| wall_time | 1.09 | 0.86-1.39 |

Verdict: **no clear difference**.

steak-pi vs pi, paired on 60 (task, rep) pairs; steak-pi cheaper in 31/60 pairs; correct 60 vs 60

| measure | steak-pi/pi | 95% CI |
|---|---|---|
| cost $ | 1.04 | 0.94-1.15 |
| total_input | 1.20 | 1.09-1.33 |
| output | 1.03 | 0.93-1.13 |
| wall_time | 1.10 | 0.88-1.37 |

Verdict: **no clear difference**.

| task | codex | dsh | pi | steak-dsh | steak-pi |
|---|---|---|---|---|---|
| h1 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h10 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h11 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h12 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h2 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h5 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h6 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h7 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h8 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h9 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t1 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t2 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t5 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t6 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t7 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t8 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

