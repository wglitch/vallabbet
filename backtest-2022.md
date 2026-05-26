# Backtest 2022 replay prototype

The val-night target is the preliminary 2022 Riksdag count from physical
polling-station districts that have `TID_RD` reporting times from Valmyndigheten.
Rows without municipality names or without `TID_RD` are excluded from the val-night target.

Replay checkpoints use the official 2022 `TID_RD` order when the timing workbook is present.
A synthetic remainder becomes counted only after all of its 2022 component districts
have appeared in that reporting order.

## Model coverage

| Model | Areas in model | Remainder areas | 2022 votes represented | Share of val-night polling-station votes |
| --- | ---: | ---: | ---: | ---: |
| A. Bara distriktsjämförbara områden | 4164 | 0 | 4,184,541 | 67.16% |
| B. Distrikt + kommunrester | 4301 | 137 | 6,229,541 | 99.98% |
| C. Distrikt + länsrester | 4185 | 21 | 6,230,608 | 100.00% |

Kommunrester built: 137. Länsrester built for the coarse alternative: 21.
District components still left after kommunrester: 2. A länsfallback after kommunrester would add 0 areas in 2022.

## Current model inside its own comparable set

| Räknat jämförelseunderlag | Råläge MAE | Nationell jämförelseprognos MAE | Justerad prognos MAE |
| --- | ---: | ---: | ---: |
| 1% | 2.61 | 1.21 | 1.20 |
| 5% | 1.32 | 0.69 | 0.47 |
| 10% | 0.95 | 0.52 | 0.37 |
| 18% | 0.62 | 0.37 | 0.23 |
| 30% | 0.36 | 0.18 | 0.13 |
| 50% | 0.15 | 0.07 | 0.05 |
| 75% | 0.06 | 0.02 | 0.02 |
| 100% | 0.00 | 0.00 | 0.00 |

## Three model inputs against whole val-night polling-station target

The local-neighbor variant for model B borrows the observed swing from the narrowest available local bucket: same municipality first, then county + municipality type + historic profile, county + type, county + profile, county, and finally national fallback.

| Simulated physical districts reported | A adjusted MAE | B adjusted MAE | C adjusted MAE | B local-neighbor MAE |
| --- | ---: | ---: | ---: | ---: |
| 1% | 1.32 | 1.28 | 1.28 | 1.28 |
| 5% | 0.48 | 0.48 | 0.41 | 0.41 |
| 10% | 0.42 | 0.38 | 0.37 | 0.46 |
| 18% | 0.33 | 0.23 | 0.26 | 0.36 |
| 30% | 0.30 | 0.17 | 0.17 | 0.20 |
| 50% | 0.25 | 0.09 | 0.12 | 0.07 |
| 75% | 0.23 | 0.06 | 0.10 | 0.03 |
| 100% | 0.22 | 0.00 | 0.00 | 0.00 |

## Whole val-night target benchmark for model A

| Simulated physical districts reported | Råläge MAE | Nationell jämförelseprognos MAE | Justerad prognos MAE |
| --- | ---: | ---: | ---: |
| 1% | 2.83 | 1.33 | 1.32 |
| 5% | 1.45 | 0.78 | 0.48 |
| 10% | 1.09 | 0.59 | 0.42 |
| 18% | 0.73 | 0.41 | 0.33 |
| 30% | 0.45 | 0.29 | 0.30 |
| 50% | 0.23 | 0.25 | 0.25 |
| 75% | 0.27 | 0.23 | 0.23 |
| 100% | 0.22 | 0.22 | 0.22 |

MAE is the mean absolute percentage-point error over the eight parties shown in the prototype.
The real 2022 reporting order now comes from Valmyndigheten's `TID_RD` file.
Wednesday collection-district votes and the final county-administration count
are intentionally outside this val-night benchmark.

## Actual 2022 reporting-time checkpoints

Uses `TID_RD` from Valmyndigheten's reporting-time workbook. The noted reporting problem window is visible in the data.
Physical districts before 21:43: 1,512. During 21:43-22:16: 165. After 22:16: 4,587.

| Time | Reported physical districts | Model areas available | Counted votes | Raw MAE | National MAE | Adjusted MAE | Local-neighbor MAE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21:00 | 51 | 42 | 20,010 | 2.67 | 1.20 | 1.19 | 1.19 |
| 21:15 | 231 | 170 | 102,344 | 1.52 | 0.78 | 0.52 | 0.47 |
| 21:30 | 790 | 541 | 391,678 | 0.90 | 0.52 | 0.31 | 0.38 |
| 21:43 | 1,513 | 997 | 796,207 | 0.60 | 0.35 | 0.20 | 0.30 |
| 22:16 | 1,677 | 1,103 | 900,876 | 0.55 | 0.30 | 0.19 | 0.26 |
| 22:30 | 2,663 | 1,756 | 1,580,109 | 0.31 | 0.19 | 0.11 | 0.10 |
| 23:00 | 4,370 | 2,904 | 2,840,743 | 0.29 | 0.13 | 0.07 | 0.03 |
| 00:00 | 5,702 | 3,858 | 4,194,607 | 0.31 | 0.12 | 0.05 | 0.04 |

## Ten random reporting-order simulations

This is a temporary stress test while the real 2022 reporting order is missing.
It shuffles physical polling-station districts with seeds `20260525` to `20260534`.
Municipality remainders still become available only when all their component districts have appeared.
Because the order is fully random, this is a friendly lower-bound test, not a realistic election-night test.
Real reporting can be geographically and administratively clustered, which is exactly why the real timestamps still matter.

Rule of thumb for reading the table: around `<= 1.0` MAE means the forecast is probably useful for the broad trend; around `<= 0.5` is much steadier.

| Reported physical districts | Median adjusted MAE | Median neighbor MAE | Neighbor wins | Worst neighbor MAE | Runs neighbor <= 1.0 | Runs neighbor <= 0.5 | Median counted votes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1% | 0.28 | 0.31 | 6/10 | 0.47 | 10/10 | 10/10 | 43,914 |
| 5% | 0.18 | 0.21 | 3/10 | 0.34 | 10/10 | 10/10 | 210,444 |
| 10% | 0.08 | 0.12 | 2/10 | 0.15 | 10/10 | 10/10 | 422,970 |
| 18% | 0.09 | 0.08 | 6/10 | 0.14 | 10/10 | 10/10 | 765,510 |
| 30% | 0.08 | 0.07 | 7/10 | 0.11 | 10/10 | 10/10 | 1,275,314 |
| 50% | 0.06 | 0.05 | 8/10 | 0.07 | 10/10 | 10/10 | 2,120,820 |
| 75% | 0.05 | 0.04 | 9/10 | 0.06 | 10/10 | 10/10 | 3,253,014 |
| 100% | 0.00 | 0.00 | 0/10 | 0.00 | 10/10 | 10/10 | 6,229,541 |

| Random run | First adjusted <= 1.0 MAE | First neighbor <= 1.0 MAE | First neighbor <= 0.5 MAE |
| ---: | ---: | ---: | ---: |
| 1 | 1% | 1% | 1% |
| 2 | 1% | 1% | 1% |
| 3 | 1% | 1% | 1% |
| 4 | 1% | 1% | 1% |
| 5 | 1% | 1% | 1% |
| 6 | 1% | 1% | 1% |
| 7 | 1% | 1% | 1% |
| 8 | 1% | 1% | 1% |
| 9 | 1% | 1% | 1% |
| 10 | 1% | 1% | 1% |

In these random simulations, every run is below 1.0 MAE from `1%` reported physical districts.
