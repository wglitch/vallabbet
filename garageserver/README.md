# Vallabbet garageserver package

This folder contains the offline/live importer package intended to run on garageserver or another internal server. It is deliberately separate from the GitHub Pages prototype.

## What it writes

The importer writes static JSON files that a web server can serve immediately:

- `../data/live/current-riksdag.json`
- `../data/live/status.json`
- `../data/live/snapshots/*.json` when snapshots are enabled

The package can be copied to garageserver later, or run from a normal clone of the repository.

## Quick local test

```powershell
cd garageserver
copy config.example.json config.json
python .\fetch_valmyndigheten.py --once --config .\config.json
```

Default `config.example.json` uses `source: fake-2022`. That means no Valmyndigheten live file is needed. The importer reads `../data/riksdag-2022-replay.json`, simulates a current file at `fakeClock`, and writes `../data/live/current-riksdag.json` plus `status.json`.

## Source modes

- `fake-2022`: test mode based on the checked-in 2022 replay file.
- `local-zip`: read a local Valmyndigheten-style zip file from `localZipFile`.
- `valmyndigheten-url`: poll `index.md5`, download a changed zip, unpack the matching JSON, and write normalized output.

The Valmyndigheten adapter is intentionally defensive because the 2026 simulation files are not available yet. It stores the raw extracted JSON under `raw` in the normalized output, and fills basic status fields where they can be inferred. Once real sample files are available, this adapter should be tightened to the exact schema.

## Suggested garageserver layout

```text
vallabbet/
  index.html
  app.js
  styles.css
  metod.html
  data/
    riksdag-2022-replay.js
    live/
      current-riksdag.json
      status.json
      snapshots/
  garageserver/
    config.json
    fetch_valmyndigheten.py
    state/
```

Run the importer as a scheduled task, service, or terminal process:

```powershell
python .\fetch_valmyndigheten.py --config .\config.json
```

For election night, keep GitHub as the code source and serve the live site from garageserver or an internal web server. GitHub Pages is not suitable for the frequently updated `current-riksdag.json` file.
