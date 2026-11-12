ParetoBench harness bench, task set 669740c30d0f28b8, 165 rows

ParetoBench **harness** bench. Task set `669740c30d0f28b8`, 165 rows, pb 0.4.1. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek-off (same route as deepseek with reasoning switched off, to make the tasks harder)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codex | 32/33 | 0.85-0.99 | 1,364,194 | 18,199,040/0 | 131,821 | 0.2047 | 0.0064 | 0.2047 | 42.9 | 110.4 | 7.0 | yes | yes |
| dsh | 28/33 | 0.69-0.93 | 868,245 | 12,985,472/0 | 173,129 | 0.1819 | 0.0065 | 0.1819 | 44.4 | 338.0 | 8.0 | no | no |
| pi | 30/33 | 0.76-0.97 | 734,515 | 5,098,496/0 | 173,837 | 0.1381 | 0.0046 | 0.1381 | 42.1 | 184.9 | 9.0 | no | yes |
| steak-dsh | 29/33 | 0.73-0.95 | 867,483 | 20,454,528/0 | 209,553 | 0.2374 | 0.0082 | 0.2374 | 40.6 | 133.4 | 8.0 | no | yes |
| steak-pi | 31/33 | 0.80-0.98 | 773,305 | 3,539,328/0 | 134,495 | 0.1120 | 0.0036 | 0.1120 | 45.4 | 130.6 | 8.0 | yes | no |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| codex | 1.00 (k=3) | 0.91 | 0 | r0=1.00 r1=0.91 r2=1.00 |
| dsh | 1.00 (k=3) | 0.64 | 0 | r0=0.91 r1=1.00 r2=0.64 |
| pi | 1.00 (k=3) | 0.73 | 0 | r0=1.00 r1=0.82 r2=0.91 |
| steak-dsh | 1.00 (k=3) | 0.73 | 0 | r0=0.91 r1=0.91 r2=0.82 |
| steak-pi | 1.00 (k=3) | 0.82 | 0 | r0=0.91 r1=1.00 r2=0.91 |

codex vs pi, paired on 33 (task, rep) pairs; codex cheaper in 19/33 pairs; correct 32 vs 30, exact sign test p=0.6250

| measure | codex/pi | 95% CI |
|---|---|---|
| cost $ | 1.48 | 0.62-3.16 |
| total_input | 3.35 | 0.62-11.67 |
| output | 0.76 | 0.57-1.04 |
| wall_time | 1.16 | 0.74-1.85 |

Verdict: **no clear difference**.

dsh vs pi, paired on 33 (task, rep) pairs; dsh cheaper in 17/33 pairs; correct 28 vs 30, exact sign test p=0.6875

| measure | dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.32 | 0.56-2.85 |
| total_input | 2.38 | 0.61-7.60 |
| output | 1.00 | 0.55-1.73 |
| wall_time | 1.57 | 0.94-2.73 |

Verdict: **no clear difference**.

steak-dsh vs pi, paired on 33 (task, rep) pairs; steak-dsh cheaper in 21/33 pairs; correct 29 vs 30, exact sign test p=1.0000

| measure | steak-dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.72 | 0.68-3.47 |
| total_input | 3.66 | 0.66-10.40 |
| output | 1.21 | 0.66-2.04 |
| wall_time | 1.40 | 0.77-2.49 |

Verdict: **no clear difference**.

steak-pi vs pi, paired on 33 (task, rep) pairs; steak-pi cheaper in 22/33 pairs; correct 31 vs 30, exact sign test p=1.0000

| measure | steak-pi/pi | 95% CI |
|---|---|---|
| cost $ | 0.81 | 0.57-1.18 |
| total_input | 0.74 | 0.36-1.65 |
| output | 0.77 | 0.62-0.99 |
| wall_time | 0.98 | 0.72-1.33 |

Verdict: **no clear difference**.

| task | codex | dsh | pi | steak-dsh | steak-pi |
|---|---|---|---|---|---|
| L1 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L10 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L11 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L2 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| L5 | 3/3 | 2/3 | 2/3 | 3/3 | 3/3 |
| L6 | 3/3 | 1/3 | 3/3 | 2/3 | 2/3 |
| L7 | 3/3 | 2/3 | 2/3 | 2/3 | 2/3 |
| L8 | 2/3 | 2/3 | 2/3 | 1/3 | 3/3 |
| L9 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

