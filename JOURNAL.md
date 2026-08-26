# Vallabbet Journal

# Current Next Step

Wait for Valmyndigheten's answer about whether matching 2014/2018 reporting-order data exists, then add a 2018-against-2014 backtest if the files are available.

---

# Journal

## 2026-08-26

Done:
- Added reporting-time replay from Valmyndigheten's 2022 `TID_RD` file.
- Added political-constellation view that compares forecast with counted vote shares.
- Clarified that uncertainty is a practical replay-calibrated error marker, not a formal confidence interval.
- Prepared backtest output for party-level error calibration.

Learned:
- The current 2022 prototype can be evaluated against preliminary election-night district totals, excluding the later county-administration count.
- A stronger method review needs at least one more historical backtest, ideally 2018 against 2014.

Next:
- Add party-specific uncertainty once the party-level backtest errors have been reviewed.
- Add 2018/2014 replay if Valmyndigheten can provide preliminary result files, reporting times or reporting order, and comparison mapping.

Open Questions:
- Did Valmyndigheten preserve 2014/2018 reporting-order timestamps or enough published snapshots to reconstruct them?
- Should a first mandate model be added before beta feedback, or kept as a separate method pass?
