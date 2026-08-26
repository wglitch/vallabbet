# Vallabbet Journal

# Current Next Step

Add result loaders for 2002, 2006 and 2010, then locate or reconstruct district comparison mappings for 2002/2006, 2006/2010 and 2010/2014.

---

# Journal

## 2026-08-26

Done:
- Added reporting-time replay from Valmyndigheten's 2022 `TID_RD` file.
- Added political-constellation view that compares forecast with counted vote shares.
- Clarified that uncertainty is a practical replay-calibrated error marker, not a formal confidence interval.
- Prepared backtest output for party-level error calibration.
- Added `historical_preflight.py` and a first 2018-against-2014 preflight/backtest report.

Learned:
- The current 2022 prototype can be evaluated against preliminary election-night district totals, excluding the later county-administration count.
- A stronger method review needs at least one more historical backtest, ideally 2018 against 2014.
- The 2018-against-2014 preflight covers 6,276,264 2018 votes, with 4,631 comparable districts and 98 municipality remainders.
- At 21:15 in the 2018-against-2014 proxy test, the hybrid UI model has 0.33 MAE against final 2018 district results.

Next:
- Add result loaders for 2002, 2006 and 2010.
- Locate or reconstruct district comparison mappings for 2002/2006, 2006/2010 and 2010/2014.
- Add party-specific uncertainty once the 2022 and 2018 historical backtest errors have been reviewed.

Open Questions:
- Did Valmyndigheten preserve 2014/2018 reporting-order timestamps or enough published snapshots to reconstruct them?
- Should a first mandate model be added before beta feedback, or kept as a separate method pass?
