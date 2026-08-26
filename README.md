# Vallabbet prototype

This is a first analysis-board prototype for Swedish election-night reporting.
It starts with the Riksdag election and replays a 2022 counting state against
the 2018 district baseline.

The Riksdag view can show an optional opinion reference from
`data/opinion-reference.json`. It is a shared editorial reference and is not
used by the forecast.

The method page summarizes the current historical backtests in separate tabs
so reviewers can compare raw counted results with the prototype forecast
without reading the generated Markdown reports.

The Riksdag view also includes a first political-constellation builder. It
sums raw and forecast vote shares for presets or any clicked party combination
and shows a calibrated uncertainty span for the whole constellation. The
political view includes a simplified mandate indicator that proportionally
allocates 349 seats between parties above the four-percent threshold. It is not
a full constituency and adjustment-seat model.

## Run

Open `index.html` directly or serve this directory locally:

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

Then open `http://127.0.0.1:4173/`.

GitHub Pages deploys the static files from `main` through
`.github/workflows/pages.yml`.

## Data

The generator expects these Valmyndigheten files in the project root:

- `preliminart-roster-per-distrikt-riksdagsvalet-2022.xlsx`
- `val2022-inrapporteringstider.xlsx`
- `2018_R_per_valdistrikt.xlsx`
- `jamforelser-2018-2022.xlsx`
- `kommungruppsindelning-2023.xlsx` from SKR
- optional `data/opinion-reference.json` for a shared editorial poll reference

Run:

```powershell
python .\build_data.py
```

It writes `data/riksdag-2022-replay.json` for server use and
`data/riksdag-2022-replay.js` so the static prototype can be opened directly.

## Current method

- Comparable physical districts are included directly. Non-comparable physical
  districts are aggregated into synthetic municipality remainder areas where a
  clean 2018 municipality remainder can be constructed.
- The raw column is the current-election share in comparison areas reported by
  the selected replay time. In this replay, current election means 2022.
- The change column compares those same comparison areas with the previous
  election baseline. In this replay, previous election means 2018.
- The prototype estimates change for uncounted comparison areas with the
  narrowest layer that has enough counted baseline: SKR municipality type plus
  historical 2018 profile, municipality type, SKR main municipality group plus
  profile, main group, historical profile, county, and finally the national
  comparison.
- Later in the replay the main forecast blends in a local comparison
  that starts with the same municipality, then broader county/type/profile
  buckets. This is meant to reduce late-evening distortion from large remaining
  municipalities.
- Historical profiles are simple first-pass buckets from the 2018 vote mix:
  `C-starkt`, `M-starkt`, `S-starkt`, `SD-starkt`, `V-MP-starkt`, and
  `Blandat`.
- The forecast applies the chosen comparison change to each uncounted area's
  previous-election baseline and combines those projected votes with counted
  current-election votes.
- The mandate indicator is a simplified national proportional seat allocation:
  parties below 4 percent are excluded, the remaining parties are rescaled, and
  349 seats are distributed by largest remainder. It is intended as a quick
  parliamentary signal, not as Valmyndigheten's exact mandate calculation.
- Uncertainty spans are first-pass empirical markers from the 2022
  replay/backtest. In the current prototype they are driven by counted votes
  and local-comparison coverage, and are shared across parties at each replay
  state. They are practical election-night error spans, not formal statistical
  confidence intervals. Late votes and the final county count remain outside
  the val-night forecast.
- The replay order uses Valmyndigheten's 2022 `TID_RD` reporting times for the
  Riksdag count when `val2022-inrapporteringstider.xlsx` is present.
- The click-through prototype now uses comparable physical districts plus
  synthetic municipality remainder areas. A municipality remainder appears only
  after all of its non-district-comparable 2022 physical districts have
  appeared in the replay.
- The replay control is a time axis from the first 2022 Riksdag report through
  01:00 on election night, with a final "slutläge" stop for late reports. With
  the municipality remainders this covers almost all physical polling-station
  votes in Valmyndigheten's preliminary val-night result.

## Backtest note

Run:

```powershell
python .\backtest.py
```

It writes `backtest-2022.md`, which compares raw counted shares, a national
comparison forecast, and the adjusted forecast at several replay checkpoints.
It reports both the comparable replay endpoint and the full preliminary
polling-station target from Valmyndigheten's 2022 district file. Collection
districts from the Wednesday/Thursday count are intentionally outside the
val-night benchmark.

The report also runs ten deterministic random reporting-order simulations.
Those are useful as a friendly stress test while real 2022 timestamps are
missing, but they should not be treated as realistic election-night order.
It also compares a local-neighbor variant that borrows swing from the same
municipality first, then progressively broader county/type/profile buckets.

The report also tests three model inputs against the whole val-night
polling-station target:

1. Comparable districts only.
2. Comparable districts plus synthetic municipality remainder areas.
3. Comparable districts plus coarser synthetic county remainder areas.

Remainder areas are counted only when every 2022 physical district included in
that remainder has appeared in the `TID_RD` reporting order. The report also
includes clock-time checkpoints around the 21:43-22:16 reporting disruption.
It now also outputs party-level absolute errors at those clock-time checkpoints
so party-specific uncertainty can be calibrated in the next method pass.

## Historical preflight

Run:

```powershell
python .\historical_preflight.py
```

It writes `historical-preflight.md`. The script is intentionally separate from
the site build and currently runs a first 2018-against-2014 model check using
Valmyndigheten's 2018 reporting-time file, 2018 district result, 2014 district
result, and the 2014/2018 mapping zip. It also runs a 2014-against-2010
fallback check using exact district-code matches plus municipality remainders,
because no 2010/2014 mapping file is loaded yet. The targets are final
district results for districts with reporting time, so these should be read as
historical proxies until preserved val-night snapshots are available.

## Next data steps

1. Confirm the public 2026 election-night result feed and data cadence.
2. Add the 2022 to 2026 comparable-district map.
3. Find or reconstruct older comparison mappings so the 2014/2010 fallback can
   be compared with a proper mapped run.
4. Calibrate confidence markers and mandate sensitivity before presenting a 2026
   forecast as more than an analytical nowcast.
