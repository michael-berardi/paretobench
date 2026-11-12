ParetoBench harness bench, task set 3c3185f48a7f97a0, 360 rows

ParetoBench **harness** bench. Task set `3c3185f48a7f97a0`, 360 rows, pb 0.4.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model haiku-or (per-token prices of the route, read from its public model listing on 2026-11-12)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codex | 60/60 | 0.94-1.00 | 198,573 | 4,264,889/197,919 | 97,125 | 0.1358 | 0.0023 | 0.1358 | 16.2 | 30.2 | 4.0 | no | no |
| dsh | 60/60 | 0.94-1.00 | 598 | 2,343,363/267,114 | 84,220 | 0.0990 | 0.0016 | 0.0990 | 12.2 | 23.0 | 4.0 | no | no |
| pi | 60/60 | 0.94-1.00 | 594 | 901,104/208,533 | 69,730 | 0.0700 | 0.0012 | 0.0700 | 9.2 | 18.4 | 4.0 | no | yes |
| steak-dsh | 60/60 | 0.94-1.00 | 614 | 1,524,810/308,143 | 80,035 | 0.0938 | 0.0016 | 0.0938 | 11.6 | 20.2 | 4.0 | no | no |
| steak-pi | 59/60 | 0.91-1.00 | 588 | 1,957,802/99,018 | 68,010 | 0.0660 | 0.0011 | 0.0660 | 11.1 | 22.2 | 4.0 | no | no |
| steak-pi-lean | 60/60 | 0.94-1.00 | 604 | 913,532/100,615 | 72,280 | 0.0579 | 0.0010 | 0.0579 | 9.9 | 18.6 | 4.0 | yes | no |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| codex | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi | 1.00 (k=3) | 0.95 | 1 | r0=1.00 r1=1.00 r2=0.95 |
| steak-pi-lean | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |

codex vs pi, paired on 60 (task, rep) pairs; codex cheaper in 5/60 pairs; correct 60 vs 60

| measure | codex/pi | 95% CI |
|---|---|---|
| cost $ | 1.94 | 1.56-2.38 |
| total_input | 4.20 | 3.40-5.19 |
| output | 1.39 | 1.25-1.55 |
| wall_time | 1.64 | 1.49-1.81 |

Verdict: **worse**.

dsh vs pi, paired on 60 (task, rep) pairs; dsh cheaper in 8/60 pairs; correct 60 vs 60

| measure | dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.41 | 1.22-1.64 |
| total_input | 2.35 | 2.03-2.70 |
| output | 1.21 | 1.08-1.38 |
| wall_time | 1.29 | 1.17-1.44 |

Verdict: **worse**.

steak-dsh vs pi, paired on 60 (task, rep) pairs; steak-dsh cheaper in 9/60 pairs; correct 60 vs 60

| measure | steak-dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.34 | 1.19-1.51 |
| total_input | 1.65 | 1.50-1.83 |
| output | 1.15 | 0.99-1.35 |
| wall_time | 1.23 | 1.09-1.40 |

Verdict: **worse**.

steak-pi vs pi, paired on 60 (task, rep) pairs; steak-pi cheaper in 17/60 pairs; correct 59 vs 60, exact sign test p=1.0000

| measure | steak-pi/pi | 95% CI |
|---|---|---|
| cost $ | 0.94 | 0.77-1.15 |
| total_input | 1.85 | 1.50-2.25 |
| output | 0.98 | 0.87-1.11 |
| wall_time | 2.03 | 1.04-4.09 |

Verdict: **no clear difference**.

steak-pi-lean vs pi, paired on 60 (task, rep) pairs; steak-pi-lean cheaper in 22/60 pairs; correct 60 vs 60

| measure | steak-pi-lean/pi | 95% CI |
|---|---|---|
| cost $ | 0.83 | 0.65-1.03 |
| total_input | 0.91 | 0.71-1.14 |
| output | 1.04 | 0.93-1.17 |
| wall_time | 1.12 | 1.00-1.27 |

Verdict: **no clear difference**.

| task | codex | dsh | pi | steak-dsh | steak-pi | steak-pi-lean |
|---|---|---|---|---|---|---|
| h1 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h10 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h11 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h12 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h2 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h5 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h6 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h7 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h8 | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 |
| h9 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t1 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t2 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t5 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t6 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t7 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t8 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

