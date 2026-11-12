ParetoBench harness bench, task set b9348b7c3c551ad3, 110 rows

ParetoBench **harness** bench. Task set `b9348b7c3c551ad3`, 110 rows, pb 0.3.1. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek (per-token prices of the route; DSH cannot send the gateway's session-affinity headers on a declared route, Steak Pi does)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dsh | 21/22 | 0.78-0.99 | 527,552 | 4,103,680/0 | 213,026 | 0.1455 | 0.0069 | 0.1455 | 55.5 | 253.8 | 8.5 | no | no |
| pi | 21/22 | 0.78-0.99 | 538,057 | 2,832,896/0 | 177,499 | 0.1217 | 0.0058 | 0.1217 | 43.1 | 234.2 | 8.5 | yes | yes |
| steak-dsh | 20/22 | 0.72-0.97 | 318,648 | 2,162,304/0 | 179,088 | 0.1115 | 0.0056 | 0.1115 | 47.2 | 202.4 | 8.0 | yes | no |
| steak-dsh-long | 20/22 | 0.72-0.97 | 382,627 | 2,648,448/0 | 176,818 | 0.1150 | 0.0058 | 0.1150 | 46.4 | 200.2 | 8.0 | no | no |
| steak-pi | 20/22 | 0.72-0.97 | 770,055 | 5,311,488/0 | 195,673 | 0.1513 | 0.0076 | 0.1513 | 55.1 | 197.5 | 10.5 | no | no |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| dsh | 1.00 (k=2) | 0.91 | 0 | r0=1.00 r1=0.91 |
| pi | 1.00 (k=2) | 0.91 | 0 | r0=0.91 r1=1.00 |
| steak-dsh | 0.91 (k=2) | 0.91 | 0 | r0=0.91 r1=0.91 |
| steak-dsh-long | 0.91 (k=2) | 0.91 | 0 | r0=0.91 r1=0.91 |
| steak-pi | 0.91 (k=2) | 0.91 | 0 | r0=0.91 r1=0.91 |

pi vs dsh, paired on 22 (task, rep) pairs; pi cheaper in 15/22 pairs; correct 21 vs 21, exact sign test p=1.0000

| measure | pi/dsh | 95% CI |
|---|---|---|
| cost $ | 0.84 | 0.70-1.02 |
| total_input | 0.73 | 0.45-1.22 |
| output | 0.83 | 0.70-1.02 |
| wall_time | 0.89 | 0.75-1.06 |

Verdict: **no clear difference**.

steak-dsh vs dsh, paired on 22 (task, rep) pairs; steak-dsh cheaper in 15/22 pairs; correct 20 vs 21, exact sign test p=1.0000

| measure | steak-dsh/dsh | 95% CI |
|---|---|---|
| cost $ | 0.77 | 0.65-0.97 |
| total_input | 0.54 | 0.38-0.82 |
| output | 0.84 | 0.72-1.03 |
| wall_time | 0.86 | 0.73-1.03 |

Verdict: **no clear difference**.

steak-dsh-long vs dsh, paired on 22 (task, rep) pairs; steak-dsh-long cheaper in 14/22 pairs; correct 20 vs 21, exact sign test p=1.0000

| measure | steak-dsh-long/dsh | 95% CI |
|---|---|---|
| cost $ | 0.79 | 0.70-0.97 |
| total_input | 0.65 | 0.51-0.96 |
| output | 0.83 | 0.75-0.98 |
| wall_time | 0.87 | 0.76-1.06 |

Verdict: **no clear difference**.

steak-pi vs dsh, paired on 22 (task, rep) pairs; steak-pi cheaper in 5/22 pairs; correct 20 vs 21, exact sign test p=1.0000

| measure | steak-pi/dsh | 95% CI |
|---|---|---|
| cost $ | 1.04 | 0.77-1.36 |
| total_input | 1.31 | 0.91-1.92 |
| output | 0.92 | 0.71-1.19 |
| wall_time | 0.94 | 0.74-1.16 |

Verdict: **no clear difference**.

| task | dsh | pi | steak-dsh | steak-dsh-long | steak-pi |
|---|---|---|---|---|---|
| L1 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L10 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L11 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L3 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L4 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L5 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L6 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L7 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| L8 | 1/2 | 1/2 | 0/2 | 0/2 | 0/2 |
| L9 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |

