ParetoBench harness bench, task set 669740c30d0f28b8, 198 rows

ParetoBench **harness** bench. Task set `669740c30d0f28b8`, 198 rows, pb 0.4.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek (per-token prices of the route; DSH cannot send the gateway's session-affinity headers on a declared route, Steak Pi does)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codex | 32/33 | 0.85-0.99 | 891,552 | 5,332,992/0 | 396,189 | 0.2560 | 0.0080 | 0.2560 | 53.9 | 345.2 | 12.0 | no | no |
| dsh | 33/33 | 0.90-1.00 | 810,190 | 4,896,128/0 | 261,834 | 0.1838 | 0.0056 | 0.1838 | 45.7 | 240.9 | 8.0 | no | no |
| pi | 33/33 | 0.90-1.00 | 661,710 | 1,529,984/0 | 183,485 | 0.1226 | 0.0037 | 0.1226 | 33.6 | 183.2 | 6.0 | no | yes |
| steak-dsh | 33/33 | 0.90-1.00 | 665,300 | 2,800,768/0 | 220,443 | 0.1475 | 0.0045 | 0.1475 | 39.2 | 137.9 | 7.0 | no | no |
| steak-pi | 33/33 | 0.90-1.00 | 575,561 | 2,484,224/0 | 150,584 | 0.1079 | 0.0033 | 0.1079 | 37.8 | 110.3 | 6.0 | yes | no |
| steak-pi-lean | 32/33 | 0.85-0.99 | 552,963 | 1,691,776/0 | 141,257 | 0.0984 | 0.0031 | 0.0984 | 29.5 | 102.6 | 7.0 | yes | yes |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| codex | 1.00 (k=3) | 0.91 | 0 | r0=1.00 r1=0.91 r2=1.00 |
| dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi-lean | 1.00 (k=3) | 0.91 | 0 | r0=1.00 r1=1.00 r2=0.91 |

codex vs pi, paired on 33 (task, rep) pairs; codex cheaper in 2/33 pairs; correct 32 vs 33, exact sign test p=1.0000

| measure | codex/pi | 95% CI |
|---|---|---|
| cost $ | 2.09 | 1.68-2.64 |
| total_input | 2.84 | 1.93-4.52 |
| output | 2.16 | 1.70-2.71 |
| wall_time | 2.33 | 1.84-2.87 |

Verdict: **worse**.

dsh vs pi, paired on 33 (task, rep) pairs; dsh cheaper in 5/33 pairs; correct 33 vs 33

| measure | dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.50 | 1.26-1.84 |
| total_input | 2.60 | 2.21-2.99 |
| output | 1.43 | 1.16-1.81 |
| wall_time | 1.48 | 1.25-1.71 |

Verdict: **worse**.

steak-dsh vs pi, paired on 33 (task, rep) pairs; steak-dsh cheaper in 13/33 pairs; correct 33 vs 33

| measure | steak-dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.20 | 0.89-1.69 |
| total_input | 1.58 | 1.08-2.43 |
| output | 1.20 | 0.84-1.76 |
| wall_time | 1.01 | 0.84-1.23 |

Verdict: **no clear difference**.

steak-pi vs pi, paired on 33 (task, rep) pairs; steak-pi cheaper in 17/33 pairs; correct 33 vs 33

| measure | steak-pi/pi | 95% CI |
|---|---|---|
| cost $ | 0.88 | 0.64-1.15 |
| total_input | 1.40 | 1.03-1.91 |
| output | 0.82 | 0.58-1.12 |
| wall_time | 0.81 | 0.69-1.01 |

Verdict: **no clear difference**.

steak-pi-lean vs pi, paired on 33 (task, rep) pairs; steak-pi-lean cheaper in 19/33 pairs; correct 32 vs 33, exact sign test p=1.0000

| measure | steak-pi-lean/pi | 95% CI |
|---|---|---|
| cost $ | 0.80 | 0.63-1.00 |
| total_input | 1.02 | 0.83-1.23 |
| output | 0.77 | 0.59-1.00 |
| wall_time | 0.76 | 0.65-0.92 |

Verdict: **no clear difference**.

| task | codex | dsh | pi | steak-dsh | steak-pi | steak-pi-lean |
|---|---|---|---|---|---|---|
| L1 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L10 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L11 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L2 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L5 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L6 | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 |
| L7 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L8 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L9 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

