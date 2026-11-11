ParetoBench harness bench, task set legacy-steak-dsh-bench, 680 rows

ParetoBench **harness** bench. Task set `legacy-steak-dsh-bench`, 680 rows, pb 0.1.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

model deepseek (per-token prices of the route; DSH cannot send the gateway's session-affinity headers on a declared route, Steak Pi does)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dsh | 100/100 | 0.96-1.00 | 763,411 | 3,653,120/0 | 122,371 | 0.1062 | 0.0011 | 0.1062 | 18.9 | 36.9 | 5.0 | no | no |
| steak-dsh | 100/100 | 0.96-1.00 | 633,313 | 2,239,744/0 | 111,793 | 0.0893 | 0.0009 | 0.0893 | 17.5 | 35.3 | 5.0 | yes | yes |
| steak-pi | 100/100 | 0.96-1.00 | 623,375 | 4,692,992/0 | 151,127 | 0.1208 | 0.0012 | 0.1208 | 18.2 | 46.6 | 5.0 | no | no |

steak-dsh vs dsh, paired on 100 (task, rep) pairs; steak-dsh cheaper in 73/100 pairs; correct 100 vs 100

| measure | steak-dsh/dsh | 95% CI |
|---|---|---|
| cost $ | 0.84 | 0.76-0.93 |
| total_input | 0.65 | 0.58-0.73 |
| output | 0.91 | 0.83-1.00 |
| wall_time | 0.95 | 0.87-1.03 |

Verdict: **better**.

steak-pi vs dsh, paired on 100 (task, rep) pairs; steak-pi cheaper in 45/100 pairs; correct 100 vs 100

| measure | steak-pi/dsh | 95% CI |
|---|---|---|
| cost $ | 1.14 | 0.99-1.29 |
| total_input | 1.20 | 1.04-1.39 |
| output | 1.23 | 1.07-1.41 |
| wall_time | 1.16 | 1.03-1.29 |

Verdict: **no clear difference**.

| task | dsh | steak-dsh | steak-pi |
|---|---|---|---|
| h1 | 5/5 | 5/5 | 5/5 |
| h10 | 5/5 | 5/5 | 5/5 |
| h11 | 5/5 | 5/5 | 5/5 |
| h12 | 5/5 | 5/5 | 5/5 |
| h2 | 5/5 | 5/5 | 5/5 |
| h3 | 5/5 | 5/5 | 5/5 |
| h4 | 5/5 | 5/5 | 5/5 |
| h5 | 5/5 | 5/5 | 5/5 |
| h6 | 5/5 | 5/5 | 5/5 |
| h7 | 5/5 | 5/5 | 5/5 |
| h8 | 5/5 | 5/5 | 5/5 |
| h9 | 5/5 | 5/5 | 5/5 |
| t1 | 5/5 | 5/5 | 5/5 |
| t2 | 5/5 | 5/5 | 5/5 |
| t3 | 5/5 | 5/5 | 5/5 |
| t4 | 5/5 | 5/5 | 5/5 |
| t5 | 5/5 | 5/5 | 5/5 |
| t6 | 5/5 | 5/5 | 5/5 |
| t7 | 5/5 | 5/5 | 5/5 |
| t8 | 5/5 | 5/5 | 5/5 |

model haiku (Claude subscription model. Stock pi has no route to it; the steak-pi arm reaches it through Steak Pi's own provider.)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | cost $ | cost $/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code | 40/40 | 0.91-1.00 | 324 | 3,898,337/190,009 | 67,018 | 0.1105 | 0.0028 | 0.1105 | 10.4 | 21.8 | 4.5 | yes | yes |
| steak-pi | 39/40 | 0.87-1.00 | 374 | 1,945,088/209,396 | 49,835 | 0.0863 | 0.0022 | 0.0863 | 15.3 | 30.4 | 4.0 | yes | no |

steak-pi vs claude-code, paired on 40 (task, rep) pairs; steak-pi cheaper in 38/40 pairs; correct 39 vs 40, exact sign test p=1.0000

| measure | steak-pi/claude-code | 95% CI |
|---|---|---|
| cost $ | 0.78 | 0.61-1.04 |
| total_input | 0.53 | 0.46-0.60 |
| output | 0.74 | 0.63-0.85 |
| wall_time | 1.39 | 1.26-1.55 |

Verdict: **no clear difference**.

| task | claude-code | steak-pi |
|---|---|---|
| h1 | 2/2 | 2/2 |
| h10 | 2/2 | 2/2 |
| h11 | 2/2 | 2/2 |
| h12 | 2/2 | 2/2 |
| h2 | 2/2 | 2/2 |
| h3 | 2/2 | 2/2 |
| h4 | 2/2 | 2/2 |
| h5 | 2/2 | 1/2 |
| h6 | 2/2 | 2/2 |
| h7 | 2/2 | 2/2 |
| h8 | 2/2 | 2/2 |
| h9 | 2/2 | 2/2 |
| t1 | 2/2 | 2/2 |
| t2 | 2/2 | 2/2 |
| t3 | 2/2 | 2/2 |
| t4 | 2/2 | 2/2 |
| t5 | 2/2 | 2/2 |
| t6 | 2/2 | 2/2 |
| t7 | 2/2 | 2/2 |
| t8 | 2/2 | 2/2 |

model qwen (flat plan; both harnesses send reasoning effort medium through the same pi-ai adapter)
weighted tokens = input 1, cacheRead 0.1, cacheWrite 1.25, output 4 (a proxy, not a price)

| harness | correct | Wilson 95% | uncached input | cached input (read/write) | output | weighted tokens | weighted tokens/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dsh | 100/100 | 0.96-1.00 | 1,017,046 | 3,377,664/0 | 142,489 | 1924768.4000 | 19247.6840 | - | 48.1 | 94.4 | 5.0 | no | no |
| steak-dsh | 100/100 | 0.96-1.00 | 781,480 | 1,585,152/0 | 99,865 | 1339455.2000 | 13394.5520 | - | 42.1 | 85.1 | 5.0 | no | no |
| steak-pi | 100/100 | 0.96-1.00 | 771,257 | 2,409,984/0 | 67,111 | 1280699.4000 | 12806.9940 | - | 30.9 | 67.3 | 4.0 | yes | yes |

steak-dsh vs dsh, paired on 100 (task, rep) pairs; steak-dsh cheaper in 78/100 pairs; correct 100 vs 100

| measure | steak-dsh/dsh | 95% CI |
|---|---|---|
| weighted tokens | 0.70 | 0.62-0.78 |
| total_input | 0.54 | 0.47-0.62 |
| output | 0.70 | 0.63-0.79 |
| wall_time | 0.84 | 0.76-0.93 |

Verdict: **better**.

steak-pi vs dsh, paired on 100 (task, rep) pairs; steak-pi cheaper in 78/100 pairs; correct 100 vs 100

| measure | steak-pi/dsh | 95% CI |
|---|---|---|
| weighted tokens | 0.67 | 0.60-0.74 |
| total_input | 0.72 | 0.65-0.81 |
| output | 0.47 | 0.42-0.52 |
| wall_time | 0.67 | 0.60-0.74 |

Verdict: **better**.

| task | dsh | steak-dsh | steak-pi |
|---|---|---|---|
| h1 | 5/5 | 5/5 | 5/5 |
| h10 | 5/5 | 5/5 | 5/5 |
| h11 | 5/5 | 5/5 | 5/5 |
| h12 | 5/5 | 5/5 | 5/5 |
| h2 | 5/5 | 5/5 | 5/5 |
| h3 | 5/5 | 5/5 | 5/5 |
| h4 | 5/5 | 5/5 | 5/5 |
| h5 | 5/5 | 5/5 | 5/5 |
| h6 | 5/5 | 5/5 | 5/5 |
| h7 | 5/5 | 5/5 | 5/5 |
| h8 | 5/5 | 5/5 | 5/5 |
| h9 | 5/5 | 5/5 | 5/5 |
| t1 | 5/5 | 5/5 | 5/5 |
| t2 | 5/5 | 5/5 | 5/5 |
| t3 | 5/5 | 5/5 | 5/5 |
| t4 | 5/5 | 5/5 | 5/5 |
| t5 | 5/5 | 5/5 | 5/5 |
| t6 | 5/5 | 5/5 | 5/5 |
| t7 | 5/5 | 5/5 | 5/5 |
| t8 | 5/5 | 5/5 | 5/5 |

