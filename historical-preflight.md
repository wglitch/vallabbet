# Historical Preflight

Purpose: check whether older election pairs can be used for model evaluation before changing the live prototype pipeline.

## Pair Availability

| Pair | Current timing file | Previous result | Current result | Mapping | Status |
| --- | --- | --- | --- | --- | --- |
| 2006 vs 2002 | yes | missing | missing | missing | needs adapter/data |
| 2010 vs 2006 | yes | missing | yes | missing | needs adapter/data |
| 2014 vs 2010 | yes | yes | yes | missing | needs adapter/data |
| 2018 vs 2014 | yes | yes | yes | yes | ready |
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

## Party-Level Absolute Errors at 2018 Clock Times

| Time | M | C | L | KD | S | V | MP | SD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21:00 | 1.18 | 2.07 | 0.06 | 0.88 | 2.01 | 0.83 | 0.90 | 0.88 |
| 21:15 | 0.53 | 0.35 | 0.07 | 0.12 | 1.04 | 0.17 | 0.08 | 0.29 |
| 21:30 | 0.15 | 0.12 | 0.05 | 0.01 | 0.28 | 0.15 | 0.27 | 0.02 |
| 22:00 | 0.24 | 0.09 | 0.05 | 0.03 | 0.02 | 0.19 | 0.18 | 0.15 |
| 22:30 | 0.13 | 0.12 | 0.04 | 0.01 | 0.00 | 0.11 | 0.14 | 0.10 |
| 23:00 | 0.11 | 0.07 | 0.04 | 0.00 | 0.00 | 0.12 | 0.12 | 0.07 |
| 00:00 | 0.04 | 0.01 | 0.01 | 0.01 | 0.00 | 0.04 | 0.05 | 0.02 |

## Next Fixes Before The Full Series

1. Add result loaders for 2002, 2006 and 2010.
2. Locate or reconstruct district comparison mappings for 2002/2006, 2006/2010 and 2010/2014.
3. Decide whether older tests should target final results, val-night XML snapshots, or both.
4. Replace this pair-specific script with a parameterized historical backtest module once at least two pairs run cleanly.
