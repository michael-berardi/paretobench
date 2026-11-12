ParetoBench harness bench, task set 3c3185f48a7f97a0, 360 rows

ParetoBench **harness** bench. Task set `3c3185f48a7f97a0`, 360 rows, pb 0.4.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek (per-token prices of the route; DSH cannot send the gateway's session-affinity headers on a declared route, Steak Pi does)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codex | 60/60 | 0.94-1.00 | 249,511 | 4,395,520/0 | 123,540 | 0.0925 | 0.0015 | 0.0925 | 31.1 | 64.6 | 6.0 | no | no |
| dsh | 60/60 | 0.94-1.00 | 152,709 | 2,334,080/0 | 73,380 | 0.0537 | 0.0009 | 0.0537 | 25.9 | 53.3 | 5.0 | no | no |
| pi | 60/60 | 0.94-1.00 | 106,927 | 933,760/0 | 59,165 | 0.0380 | 0.0006 | 0.0380 | 22.1 | 41.2 | 5.0 | no | no |
| steak-dsh | 60/60 | 0.94-1.00 | 128,550 | 1,316,736/0 | 54,277 | 0.0382 | 0.0006 | 0.0382 | 24.0 | 43.0 | 5.0 | no | no |
| steak-pi | 60/60 | 0.94-1.00 | 113,053 | 4,523,520/0 | 64,426 | 0.0588 | 0.0010 | 0.0588 | 25.8 | 48.1 | 5.0 | no | no |
| steak-pi-lean | 60/60 | 0.94-1.00 | 78,373 | 913,152/0 | 46,427 | 0.0305 | 0.0005 | 0.0305 | 21.4 | 43.7 | 4.0 | yes | yes |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| codex | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi-lean | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |

codex vs pi, paired on 60 (task, rep) pairs; codex cheaper in 5/60 pairs; correct 60 vs 60

| measure | codex/pi | 95% CI |
|---|---|---|
| cost $ | 2.43 | 1.96-2.99 |
| total_input | 4.46 | 3.91-5.07 |
| output | 2.09 | 1.61-2.71 |
| wall_time | 1.55 | 1.33-1.84 |

Verdict: **worse**.

dsh vs pi, paired on 60 (task, rep) pairs; dsh cheaper in 8/60 pairs; correct 60 vs 60

| measure | dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.41 | 1.16-1.70 |
| total_input | 2.39 | 2.06-2.72 |
| output | 1.24 | 1.00-1.53 |
| wall_time | 1.23 | 1.08-1.38 |

Verdict: **worse**.

steak-dsh vs pi, paired on 60 (task, rep) pairs; steak-dsh cheaper in 26/60 pairs; correct 60 vs 60

| measure | steak-dsh/pi | 95% CI |
|---|---|---|
| cost $ | 1.01 | 0.81-1.22 |
| total_input | 1.39 | 1.17-1.61 |
| output | 0.92 | 0.71-1.14 |
| wall_time | 1.00 | 0.88-1.12 |

Verdict: **no clear difference**.

steak-pi vs pi, paired on 60 (task, rep) pairs; steak-pi cheaper in 6/60 pairs; correct 60 vs 60

| measure | steak-pi/pi | 95% CI |
|---|---|---|
| cost $ | 1.55 | 1.33-1.79 |
| total_input | 4.46 | 3.98-4.95 |
| output | 1.09 | 0.92-1.28 |
| wall_time | 1.21 | 1.09-1.33 |

Verdict: **worse**.

steak-pi-lean vs pi, paired on 60 (task, rep) pairs; steak-pi-lean cheaper in 33/60 pairs; correct 60 vs 60

| measure | steak-pi-lean/pi | 95% CI |
|---|---|---|
| cost $ | 0.80 | 0.67-0.96 |
| total_input | 0.95 | 0.80-1.10 |
| output | 0.78 | 0.63-0.97 |
| wall_time | 0.96 | 0.84-1.07 |

Verdict: **better**.

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
| h8 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| h9 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t1 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t2 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t5 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t6 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t7 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| t8 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

