# Vallabbet prototype

This is a first analysis-board prototype for Swedish election-night reporting.
It starts with the Riksdag election and replays a 2022 counting state against
the 2018 district baseline.

The Riksdag view includes an optional opinion-reference toggle. It is a
placeholder for a future poll average or selected polling source and is not
used by the forecast.

The Riksdag view also includes a first political-constellation builder. It
sums raw and forecast vote shares for presets or any clicked party combination.
It deliberately does not infer mandates, thresholds, or government viability
until the mandate model has been reviewed.

## Run

Open `index.html` directly or serve this directory locally:

```powershell
& 'C:\Users\wackn\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m http.server 4173 --bind 127.0.0.1
```

Then open `http://127.0.0.1:4173/`.

## Data

The generator expects these Valmyndigheten files in the project root:

- `preliminart-roster-per-distrikt-riksdagsvalet-2022.xlsx`
- `2018_R_per_valdistrikt.xlsx`
- `jamforelser-2018-2022.xlsx`
- `kommungruppsindelning-2023.xlsx` from SKR

Run:

```powershell
& 'C:\Users\wackn\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\build_data.py
```

It writes `data/riksdag-2022-replay.json` for server use and
`data/riksdag-2022-replay.js` so the static prototype can be opened directly.

## Current method

- Comparable physical districts are included directly. Non-comparable physical
  districts are aggregated into synthetic municipality remainder areas where a
  clean 2018 municipality remainder can be constructed.
- The raw column is the 2022 share in comparison areas counted at the slider
  state.
- The change column compares those same comparison areas with their 2018
  baseline.
- The prototype estimates change for uncounted comparison areas with the
  narrowest layer that has enough counted baseline: SKR municipality type plus
  historical 2018 profile, municipality type, SKR main municipality group plus
  profile, main group, historical profile, county, and finally the national
  comparison.
- Historical profiles are simple first-pass buckets from the 2018 vote mix:
  `C-starkt`, `M-starkt`, `S-starkt`, `SD-starkt`, `V-MP-starkt`, and
  `Blandat`.
- The forecast applies the chosen comparison change to each uncounted area's 2018
  baseline and combines those projected votes with counted 2022 votes.
- Confidence markers are first-pass coverage markers. They reflect counted vote
  volume and how much of the remaining baseline can use a stratified estimate
  instead of the national fallback.
- The replay order is a size-first simulator using 2022 valid votes for
  physical districts. It is not yet the true order in which districts reported
  on election night.
- The click-through prototype now uses comparable physical districts plus
  synthetic municipality remainder areas. A municipality remainder appears only
  after all of its non-district-comparable 2022 physical districts have
  appeared in the replay.
- `100%` in the slider means all comparison areas in the prototype. With the
  municipality remainders this covers almost all physical polling-station votes
  in Valmyndigheten's preliminary val-night result.

## Backtest note

Run:

```powershell
& 'C:\Users\wackn\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\backtest.py
```

It writes `backtest-2022.md`, which compares raw counted shares, a national
comparison forecast, and the adjusted forecast at several replay checkpoints.
It reports both the comparable replay endpoint and the full preliminary
polling-station target from Valmyndigheten's 2022 district file. Collection
districts from the Wednesday/Thursday count are intentionally outside the
val-night benchmark.

The report also tests three model inputs against the whole val-night
polling-station target:

1. Comparable districts only.
2. Comparable districts plus synthetic municipality remainder areas.
3. Comparable districts plus coarser synthetic county remainder areas.

Remainder areas are counted only when every 2022 physical district included in
that remainder has appeared in the simulated replay order. Actual 2022
reporting timestamps are still the missing review input.

## Next data steps

1. Import real 2022 protocol timestamps for replay verification.
2. Confirm the public 2026 election-night result feed and data cadence.
3. Add the 2022 to 2026 comparable-district map.
4. Calibrate confidence markers and mandate sensitivity before presenting a 2026
   forecast as more than an analytical nowcast.
