# Historical Preflight

Purpose: check whether older election pairs can be used for model evaluation before changing the live prototype pipeline.

## Pair Availability

| Pair | Current timing file | Previous result | Current result | Mapping | Status |
| --- | --- | --- | --- | --- | --- |
| 2006 vs 2002 | yes | missing | missing | missing | needs adapter/data |
| 2010 vs 2006 | yes | missing | yes | missing | needs adapter/data |
| 2014 vs 2010 | yes | yes | yes | missing | fallback ready |
| 2018 vs 2014 | yes | yes | yes | yes | ready with mapping |
| 2022 vs 2018 | yes | yes | yes | yes | needs adapter/data |

## 2018 vs 2014 Data Coverage

| Metric | Value |
| --- | ---: |
| current districts | 6,057 |
| current with timing | 6,004 |
| previous districts | 6,015 |
| mapping rows | 6,949 |
| mapping current codes | 5,998 |
| comparable districts | 4,631 |
| municipality remainders | 98 |
| model areas | 4,729 |
| target votes | 6,276,264 |
| model votes | 6,276,264 |
| model vote coverage | 100.00% |

## 2018 vs 2014 Clock-Time Backtest

Target is final 2018 district result for districts with reporting time. This is a historical proxy, not a preserved 2018 val-night snapshot.

| Time | Model areas counted | Counted votes | Raw MAE | National MAE | Adjusted MAE | Local-neighbor MAE | Hybrid UI MAE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21:00 | 79 | 35,344 | 2.63 | 1.07 | 1.10 | 1.04 | 1.10 |
| 21:15 | 267 | 160,918 | 1.58 | 0.74 | 0.33 | 0.37 | 0.33 |
| 21:30 | 681 | 499,743 | 1.01 | 0.42 | 0.13 | 0.17 | 0.13 |
| 22:00 | 2,254 | 2,083,436 | 0.39 | 0.18 | 0.14 | 0.11 | 0.12 |
| 22:30 | 3,511 | 3,579,315 | 0.32 | 0.17 | 0.12 | 0.07 | 0.08 |
| 23:00 | 4,184 | 4,551,634 | 0.31 | 0.17 | 0.11 | 0.05 | 0.07 |
| 00:00 | 4,590 | 5,702,908 | 0.13 | 0.09 | 0.03 | 0.02 | 0.02 |

## 2018 vs 2014 Model-Area Checkpoints

| Counted model areas | Raw MAE | National MAE | Adjusted MAE | Local-neighbor MAE | Hybrid UI MAE |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1% | 2.68 | 1.05 | 1.05 | 1.05 | 1.05 |
| 5% | 1.80 | 0.85 | 0.39 | 0.51 | 0.39 |
| 10% | 1.33 | 0.56 | 0.15 | 0.28 | 0.15 |
| 18% | 0.89 | 0.39 | 0.15 | 0.17 | 0.15 |
| 30% | 0.57 | 0.26 | 0.13 | 0.14 | 0.13 |
| 50% | 0.38 | 0.17 | 0.14 | 0.11 | 0.12 |
| 75% | 0.32 | 0.17 | 0.12 | 0.07 | 0.08 |
| 100% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## 2018 vs 2014 Party-Level Absolute Errors at Clock Times

| Time | M | C | L | KD | S | V | MP | SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21:00 | 1.18 | 2.07 | 0.06 | 0.88 | 2.01 | 0.83 | 0.90 | 0.88 |
| 21:15 | 0.53 | 0.35 | 0.07 | 0.12 | 1.04 | 0.17 | 0.08 | 0.29 |
| 21:30 | 0.15 | 0.12 | 0.05 | 0.01 | 0.28 | 0.15 | 0.27 | 0.02 |
| 22:00 | 0.24 | 0.09 | 0.05 | 0.03 | 0.02 | 0.19 | 0.18 | 0.15 |
| 22:30 | 0.13 | 0.12 | 0.04 | 0.01 | 0.00 | 0.11 | 0.14 | 0.10 |
| 23:00 | 0.11 | 0.07 | 0.04 | 0.00 | 0.00 | 0.12 | 0.12 | 0.07 |
| 00:00 | 0.04 | 0.01 | 0.01 | 0.01 | 0.00 | 0.04 | 0.05 | 0.02 |

## 2014 vs 2010 Data Coverage

| Metric | Value |
| --- | ---: |
| current districts | 6,015 |
| current with timing | 5,837 |
| previous districts | 5,854 |
| direct code matches | 5,169 |
| current timed not direct | 668 |
| comparable districts | 5,169 |
| municipality remainders | 40 |
| model areas | 5,209 |
| target votes | 6,054,541 |
| model votes | 6,050,667 |
| model vote coverage | 99.94% |

## 2014 vs 2010 Clock-Time Backtest

Target is final 2014 district result for districts with reporting time. Because no 2010/2014 mapping file is loaded, this fallback uses exact district-code matches plus municipality remainders.

| Time | Model areas counted | Counted votes | Raw MAE | National MAE | Adjusted MAE | Local-neighbor MAE | Hybrid UI MAE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21:00 | 181 | 91,637 | 2.31 | 0.57 | 0.74 | 0.76 | 0.74 |
| 21:15 | 550 | 369,130 | 1.50 | 0.35 | 0.28 | 0.26 | 0.28 |
| 21:30 | 1,338 | 1,087,720 | 1.01 | 0.22 | 0.24 | 0.17 | 0.23 |
| 22:00 | 3,347 | 3,204,484 | 0.42 | 0.12 | 0.14 | 0.20 | 0.14 |
| 22:30 | 4,533 | 4,616,980 | 0.22 | 0.09 | 0.10 | 0.19 | 0.13 |
| 23:00 | 4,958 | 5,212,117 | 0.18 | 0.08 | 0.09 | 0.18 | 0.12 |
| 00:00 | 5,159 | 5,616,474 | 0.13 | 0.05 | 0.07 | 0.18 | 0.12 |

## 2014 vs 2010 Model-Area Checkpoints

| Counted model areas | Raw MAE | National MAE | Adjusted MAE | Local-neighbor MAE | Hybrid UI MAE |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1% | 2.92 | 0.81 | 0.80 | 0.80 | 0.80 |
| 5% | 2.16 | 0.51 | 0.70 | 0.49 | 0.70 |
| 10% | 1.58 | 0.37 | 0.31 | 0.29 | 0.31 |
| 18% | 1.19 | 0.23 | 0.22 | 0.18 | 0.22 |
| 30% | 0.93 | 0.19 | 0.22 | 0.16 | 0.21 |
| 50% | 0.54 | 0.15 | 0.15 | 0.22 | 0.15 |
| 75% | 0.33 | 0.12 | 0.12 | 0.20 | 0.14 |
| 100% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## 2014 vs 2010 Party-Level Absolute Errors at Clock Times

| Time | M | C | L | KD | S | V | MP | SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21:00 | 1.39 | 0.10 | 0.44 | 0.28 | 0.60 | 0.34 | 0.19 | 2.59 |
| 21:15 | 0.66 | 0.12 | 0.01 | 0.06 | 0.02 | 0.20 | 0.05 | 1.11 |
| 21:30 | 0.44 | 0.04 | 0.14 | 0.07 | 0.34 | 0.08 | 0.15 | 0.59 |
| 22:00 | 0.44 | 0.03 | 0.09 | 0.07 | 0.01 | 0.18 | 0.24 | 0.04 |
| 22:30 | 0.38 | 0.02 | 0.06 | 0.08 | 0.02 | 0.19 | 0.23 | 0.03 |
| 23:00 | 0.35 | 0.01 | 0.04 | 0.08 | 0.00 | 0.19 | 0.21 | 0.04 |
| 00:00 | 0.26 | 0.02 | 0.02 | 0.09 | 0.08 | 0.17 | 0.22 | 0.08 |

## Next Fixes Before The Full Series

1. Add result loaders for 2002 and 2006.
2. Locate or reconstruct district comparison mappings for 2002/2006, 2006/2010 and 2010/2014.
3. Decide whether older tests should target final results, val-night XML snapshots, or both.
4. Replace this pair-specific script with a parameterized historical backtest module once at least two pairs run cleanly.
