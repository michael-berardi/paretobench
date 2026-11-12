ParetoBench harness bench, task set 669740c30d0f28b8, 165 rows

ParetoBench **harness** bench. Task set `669740c30d0f28b8`, 165 rows, pb 0.4.1. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek (per-token prices of the route; DSH cannot send the gateway's session-affinity headers on a declared route, Steak Pi does)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codex | 32/33 | 0.85-0.99 | 749,048 | 4,728,576/0 | 408,381 | 0.2541 | 0.0079 | 0.2541 | 74.1 | 552.7 | 13.0 | no | no |
| dsh | 33/33 | 0.90-1.00 | 843,671 | 8,038,144/0 | 346,344 | 0.2429 | 0.0074 | 0.2429 | 66.3 | 299.9 | 9.0 | no | no |
| pi | 33/33 | 0.90-1.00 | 605,842 | 2,328,704/0 | 215,730 | 0.1407 | 0.0043 | 0.1407 | 37.2 | 253.9 | 7.0 | no | yes |
| steak-dsh | 31/33 | 0.80-0.98 | 653,906 | 2,989,312/0 | 224,337 | 0.1500 | 0.0048 | 0.1500 | 57.4 | 203.8 | 8.0 | no | no |
| steak-pi | 33/33 | 0.90-1.00 | 798,511 | 1,977,344/0 | 164,440 | 0.1201 | 0.0036 | 0.1201 | 44.1 | 187.7 | 7.0 | yes | no |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| codex | 1.00 (k=3) | 0.91 | 1 | r0=1.00 r1=1.00 r2=0.91 |
| dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-dsh | 1.00 (k=3) | 0.91 | 0 | r0=0.91 r1=1.00 r2=0.91 |
| steak-pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |

codex vs pi, paired on 33 (task, rep) pairs; codex cheaper in 4/33 pairs; correct 32 vs 33, exact sign test p=1.0000

| measure | codex/pi | 95% CI |
|---|---|---|
| cost $ | 1.81 | 1.40-2.21 |
| total_input | 1.87 | 1.43-2.47 |
| output | 1.89 | 1.43-2.32 |
| wall_time | 2.45 | 1.72-3.65 |

Verdict: **worse**.

dsh vs pi, paired on 33 (task, rep) pairs; dsh cheaper in 4/33 pairs; correct 33 vs 33

| measure | dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.73 | 1.23-2.58 |
| total_input | 3.03 | 1.61-5.95 |
| output | 1.61 | 1.17-2.37 |
| wall_time | 1.47 | 1.02-2.08 |

Verdict: **worse**.

steak-dsh vs pi, paired on 33 (task, rep) pairs; steak-dsh cheaper in 15/33 pairs; correct 31 vs 33, exact sign test p=0.5000

| measure | steak-dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.07 | 0.83-1.36 |
| total_input | 1.24 | 0.90-1.67 |
| output | 1.04 | 0.80-1.32 |
| wall_time | 1.03 | 0.82-1.31 |

Verdict: **no clear difference**.

steak-pi vs pi, paired on 33 (task, rep) pairs; steak-pi cheaper in 21/33 pairs; correct 33 vs 33

| measure | steak-pi/pi | 95% CI |
|---|---|---|
| cost $ | 0.85 | 0.74-1.03 |
| total_input | 0.95 | 0.74-1.27 |
| output | 0.76 | 0.67-0.91 |
| wall_time | 0.83 | 0.64-1.09 |

Verdict: **no clear difference**.

| task | codex | dsh | pi | steak-dsh | steak-pi |
|---|---|---|---|---|---|
| L1 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L10 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L11 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L2 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L5 | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L6 | 3/3 | 3/3 | 3/3 | 1/3 | 3/3 |
| L7 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L8 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L9 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

