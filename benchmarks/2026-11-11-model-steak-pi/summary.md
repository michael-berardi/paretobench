ParetoBench model bench, task set 3c3185f48a7f97a0, 180 rows

ParetoBench **model** bench. Task set `3c3185f48a7f97a0`, 180 rows, pb 0.1.0. Bootstrap: 5000 resamples of (task, rep) pairs, seed 1.

harness steak-pi (at least one model is on a flat plan with no per-token price, so every model is compared in weighted tokens; dollars are shown beside each priced model)
weighted tokens = input 1, cacheRead 0.1, cacheWrite 1.25, output 4 (a proxy, not a price)

| model | correct | Wilson 95% | uncached input | cached input (read/write) | output | weighted tokens | weighted tokens/correct | list price $ | median s | p90 s | median turns | cost frontier | time frontier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek | 60/60 | 0.94-1.00 | 430,471 | 2,757,888/0 | 90,529 | 1068375.8000 | 17806.2633 | 0.0741 | 18.2 | 39.0 | 6.0 | no | yes |
| haiku | 58/60 | 0.89-0.99 | 556 | 3,065,250/334,424 | 72,951 | 1016915.0000 | 17533.0172 | 0.1341 | 17.4 | 59.2 | 4.0 | no | yes |
| qwen | 60/60 | 0.94-1.00 | 521,053 | 1,610,496/0 | 46,165 | 866762.6000 | 14446.0433 | - | 39.5 | 85.6 | 5.0 | yes | no |

haiku vs deepseek, paired on 60 (task, rep) pairs; haiku cheaper in 40/60 pairs; correct 58 vs 60, exact sign test p=0.5000

| measure | haiku/deepseek | 95% CI |
|---|---|---|
| weighted tokens | 0.95 | 0.76-1.21 |
| total_input | 1.07 | 0.92-1.23 |
| output | 0.81 | 0.71-0.91 |
| wall_time | 1.49 | 1.03-2.30 |

Verdict: **no clear difference**.

qwen vs deepseek, paired on 60 (task, rep) pairs; qwen cheaper in 35/60 pairs; correct 60 vs 60

| measure | qwen/deepseek | 95% CI |
|---|---|---|
| weighted tokens | 0.81 | 0.72-0.92 |
| total_input | 0.67 | 0.59-0.76 |
| output | 0.51 | 0.46-0.58 |
| wall_time | 2.12 | 1.84-2.50 |

Verdict: **better**.

| task | deepseek | haiku | qwen |
|---|---|---|---|
| h1 | 3/3 | 3/3 | 3/3 |
| h10 | 3/3 | 3/3 | 3/3 |
| h11 | 3/3 | 3/3 | 3/3 |
| h12 | 3/3 | 3/3 | 3/3 |
| h2 | 3/3 | 3/3 | 3/3 |
| h3 | 3/3 | 3/3 | 3/3 |
| h4 | 3/3 | 3/3 | 3/3 |
| h5 | 3/3 | 1/3 | 3/3 |
| h6 | 3/3 | 3/3 | 3/3 |
| h7 | 3/3 | 3/3 | 3/3 |
| h8 | 3/3 | 3/3 | 3/3 |
| h9 | 3/3 | 3/3 | 3/3 |
| t1 | 3/3 | 3/3 | 3/3 |
| t2 | 3/3 | 3/3 | 3/3 |
| t3 | 3/3 | 3/3 | 3/3 |
| t4 | 3/3 | 3/3 | 3/3 |
| t5 | 3/3 | 3/3 | 3/3 |
| t6 | 3/3 | 3/3 | 3/3 |
| t7 | 3/3 | 3/3 | 3/3 |
| t8 | 3/3 | 3/3 | 3/3 |

