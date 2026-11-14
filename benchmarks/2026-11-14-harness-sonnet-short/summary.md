ParetoBench harness bench, task set 3c3185f48a7f97a0, 300 rows

ParetoBench **harness** bench. Task set `3c3185f48a7f97a0`, 300 rows, pb 0.4.2. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model sonnet (Claude subscription model (Claude Code login). Rates are the public list price per token, for comparison only; runs draw on the plan. Stock pi and stock dsh have no route to it.)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code | 60/60 | 0.94-1.00 | 430 | 4,776,350/116,221 | 44,464 | 1.2137 | 0.0202 | 1.2137 | 9.4 | 13.6 | 4.0 | no | no |
| codex | 60/60 | 0.94-1.00 | 396 | 1,892,813/137,284 | 30,044 | 0.8337 | 0.0139 | 0.8337 | 8.4 | 11.9 | 3.0 | no | yes |
| steak-dsh | 60/60 | 0.94-1.00 | 422 | 1,135,733/119,727 | 35,472 | 0.7685 | 0.0128 | 0.7685 | 10.1 | 16.5 | 3.0 | no | no |
| steak-pi | 60/60 | 0.94-1.00 | 418 | 835,605/79,892 | 29,802 | 0.5821 | 0.0097 | 0.5821 | 9.1 | 14.1 | 3.0 | yes | no |
| steak-pi-lean | 60/60 | 0.94-1.00 | 418 | 822,041/83,548 | 29,816 | 0.5901 | 0.0098 | 0.5901 | 9.1 | 13.5 | 3.0 | no | no |

| harness | pass@k | pass^k | timeouts | correct per repeat |
|---|---|---|---|---|
| claude-code | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| codex | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-dsh | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |
| steak-pi-lean | 1.00 (k=3) | 1.00 | 0 | r0=1.00 r1=1.00 r2=1.00 |

codex vs claude-code, paired on 60 (task, rep) pairs; codex cheaper in 52/60 pairs; correct 60 vs 60

| measure | codex/claude-code | 95% CI |
|---|---|---|
| cost $ | 0.69 | 0.64-0.74 |
| total_input | 0.41 | 0.39-0.44 |
| output | 0.68 | 0.62-0.73 |
| wall_time | 0.89 | 0.83-0.95 |

Verdict: **better**.

steak-dsh vs claude-code, paired on 60 (task, rep) pairs; steak-dsh cheaper in 59/60 pairs; correct 60 vs 60

| measure | steak-dsh/claude-code | 95% CI |
|---|---|---|
| cost $ | 0.63 | 0.57-0.71 |
| total_input | 0.26 | 0.24-0.28 |
| output | 0.80 | 0.75-0.85 |
| wall_time | 1.11 | 1.05-1.18 |

Verdict: **better**.

steak-pi vs claude-code, paired on 60 (task, rep) pairs; steak-pi cheaper in 60/60 pairs; correct 60 vs 60

| measure | steak-pi/claude-code | 95% CI |
|---|---|---|
| cost $ | 0.48 | 0.44-0.52 |
| total_input | 0.19 | 0.17-0.20 |
| output | 0.67 | 0.61-0.74 |
| wall_time | 0.96 | 0.89-1.03 |

Verdict: **better**.

steak-pi-lean vs claude-code, paired on 60 (task, rep) pairs; steak-pi-lean cheaper in 60/60 pairs; correct 60 vs 60

| measure | steak-pi-lean/claude-code | 95% CI |
|---|---|---|
| cost $ | 0.49 | 0.45-0.53 |
| total_input | 0.19 | 0.17-0.20 |
| output | 0.67 | 0.61-0.74 |
| wall_time | 0.95 | 0.88-1.02 |

Verdict: **better**.

| task | claude-code | codex | steak-dsh | steak-pi | steak-pi-lean |
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

