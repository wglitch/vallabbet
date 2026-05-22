# Backtest 2022 replay prototype

The val-night target is the preliminary 2022 Riksdag count from physical
polling-station districts in Valmyndigheten's preliminary district file.
Collection-district rows ending in `-0000` are excluded.

All replay checkpoints still use a size-based order of 2022 physical
districts. A synthetic remainder becomes counted only after all of its
2022 component districts have appeared in that simulated order.

## Model coverage

| Model | Areas in model | Remainder areas | 2022 votes represented | Share of val-night polling-station votes |
| --- | ---: | ---: | ---: | ---: |
| A. Bara distriktsjämförbara områden | 4164 | 0 | 4,184,541 | 66.57% |
| B. Distrikt + kommunrester | 4303 | 139 | 6,284,970 | 99.98% |
| C. Distrikt + länsrester | 4185 | 21 | 6,286,037 | 100.00% |

Kommunrester built: 139. Länsrester built for the coarse alternative: 21.
District components still left after kommunrester: 2. A länsfallback after kommunrester would add 0 areas in 2022.

## Current model inside its own comparable set

| Räknat jämförelseunderlag | Råläge MAE | Nationell jämförelseprognos MAE | Justerad prognos MAE |
| --- | ---: | ---: | ---: |
| 1% | 2.56 | 1.71 | 1.69 |
| 5% | 2.06 | 1.11 | 1.09 |
| 10% | 2.16 | 1.07 | 0.95 |
| 18% | 1.81 | 0.81 | 0.57 |
| 30% | 1.43 | 0.57 | 0.31 |
| 50% | 0.85 | 0.31 | 0.16 |
| 75% | 0.46 | 0.12 | 0.06 |
| 100% | 0.00 | 0.00 | 0.00 |

## Three model inputs against whole val-night polling-station target

| Simulated physical districts reported | A adjusted MAE | B adjusted MAE | C adjusted MAE |
| --- | ---: | ---: | ---: |
| 1% | 1.78 | 1.79 | 1.79 |
| 5% | 1.13 | 1.15 | 1.15 |
| 10% | 1.00 | 0.94 | 0.80 |
| 18% | 0.62 | 0.53 | 0.48 |
| 30% | 0.41 | 0.31 | 0.29 |
| 50% | 0.31 | 0.26 | 0.17 |
| 75% | 0.27 | 0.20 | 0.10 |
| 100% | 0.24 | 0.00 | 0.00 |

## Whole val-night target benchmark for model A

| Simulated physical districts reported | Råläge MAE | Nationell jämförelseprognos MAE | Justerad prognos MAE |
| --- | ---: | ---: | ---: |
| 1% | 2.80 | 1.79 | 1.78 |
| 5% | 2.20 | 1.19 | 1.13 |
| 10% | 2.28 | 1.11 | 1.00 |
| 18% | 1.93 | 0.86 | 0.62 |
| 30% | 1.53 | 0.62 | 0.41 |
| 50% | 0.94 | 0.37 | 0.31 |
| 75% | 0.45 | 0.28 | 0.27 |
| 100% | 0.24 | 0.24 | 0.24 |

MAE is the mean absolute percentage-point error over the eight parties shown in the prototype.
The real 2022 reporting order is still the missing verification input.
Wednesday collection-district votes and the final county-administration count
are intentionally outside this val-night benchmark.
