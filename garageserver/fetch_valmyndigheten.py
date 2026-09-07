from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


DEFAULT_CONFIG = "config.json"

PARTY_META = {
    "M": {"name": "Moderaterna", "color": "#3b82d0"},
    "C": {"name": "Centerpartiet", "color": "#1c8a53"},
    "L": {"name": "Liberalerna", "color": "#147cc1"},
    "KD": {"name": "Kristdemokraterna", "color": "#264e96"},
    "S": {"name": "Socialdemokraterna", "color": "#d83c45"},
    "V": {"name": "Vänsterpartiet", "color": "#9d2235"},
    "MP": {"name": "Miljöpartiet", "color": "#49a13a"},
    "SD": {"name": "Sverigedemokraterna", "color": "#d6ad2b"},
}

COUNTY_NAMES = {
    "01": "Stockholm",
    "03": "Uppsala",
    "04": "Södermanland",
    "05": "Östergötland",
    "06": "Jönköping",
    "07": "Kronoberg",
    "08": "Kalmar",
    "09": "Gotland",
    "10": "Blekinge",
    "12": "Skåne",
    "13": "Halland",
    "14": "Västra Götaland",
    "17": "Värmland",
    "18": "Örebro",
    "19": "Västmanland",
    "20": "Dalarna",
    "21": "Gävleborg",
    "22": "Västernorrland",
    "23": "Jämtland",
    "24": "Västerbotten",
    "25": "Norrbotten",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def resolve(base: Path, configured: str) -> Path:
    path = Path(configured)
    return path if path.is_absolute() else (base / path).resolve()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError:
        return {}


def write_status(public_dir: Path, status: dict) -> None:
    write_json_atomic(public_dir / "status.json", status)


def save_snapshot(snapshot_dir: Path, payload: dict, prefix: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = snapshot_dir / f"{timestamp}-{prefix}.json"
    write_json_atomic(target, payload)
    return target


def fake_2022_payload(config: dict, base_dir: Path) -> tuple[dict, dict]:
    replay_path = resolve(base_dir, config["fakeReplayFile"])
    replay = load_json(replay_path)
    cutoff = datetime.fromisoformat(config["fakeClock"])
    reported = []
    pending = []
    for area in replay["districts"]:
        raw_time = area.get("reportingTimeRD") or area.get("reportingTime")
        if raw_time and datetime.fromisoformat(raw_time) <= cutoff:
            reported.append(area)
        else:
            pending.append(area)

    payload = {
        "schema": "vallabbet-live-current-v1",
        "mode": "fake-2022",
        "election": "RD",
        "year": 2022,
        "generatedAt": utc_now(),
        "sourceUpdatedAt": config["fakeClock"],
        "source": "Fake current file generated from data/riksdag-2022-replay.json",
        "counts": {
            "reportedAreas": len(reported),
            "pendingAreas": len(pending),
            "validReportedVotes": sum(area.get("valid22", 0) for area in reported),
        },
        "areas": reported,
    }
    status = {
        "ok": True,
        "mode": "fake-2022",
        "updatedAt": utc_now(),
        "sourceUpdatedAt": config["fakeClock"],
        "reportedAreas": len(reported),
        "pendingAreas": len(pending),
        "validReportedVotes": payload["counts"]["validReportedVotes"],
        "message": "Generated fake live current-riksdag.json from replay data.",
    }
    return payload, status


def find_member(zip_file: zipfile.ZipFile, pattern: str) -> str:
    candidates = [name for name in zip_file.namelist() if pattern in Path(name).name]
    if not candidates:
        candidates = [name for name in zip_file.namelist() if name.lower().endswith(".json")]
    if not candidates:
        raise ValueError(f"No JSON member matching {pattern!r} found in zip")
    return sorted(candidates)[0]


def load_baseline_metadata(config: dict, base_dir: Path) -> dict:
    replay_file = config.get("baselineReplayFile")
    if not replay_file:
        return {"by_municipality": {}, "by_district": {}}
    path = resolve(base_dir, replay_file)
    if not path.exists():
        return {"by_municipality": {}, "by_district": {}}
    replay = load_json(path)
    by_municipality = {}
    by_district = {}
    for area in replay.get("districts", []):
        municipality_code = str(area.get("municipalityCode") or "")
        if municipality_code and municipality_code not in by_municipality:
            by_municipality[municipality_code] = {
                "municipality": area.get("municipality") or municipality_code,
                "county": area.get("county") or COUNTY_NAMES.get(municipality_code[:2], municipality_code[:2]),
                "constituency": area.get("constituency") or area.get("county") or "",
                "municipalityGroupCode": area.get("municipalityGroupCode") or "NA",
                "municipalityBand": area.get("municipalityBand") or "Okänd kommuntyp",
                "municipalityType": area.get("municipalityType") or "Okänd kommuntyp",
            }
        by_district[str(area.get("id") or "")] = area
    return {"by_municipality": by_municipality, "by_district": by_district}


def party_votes(section: dict, field: str) -> dict[str, int]:
    votes = {party: 0 for party in PARTY_META}
    for row in section.get("partiRoster") or []:
        party = row.get("partiforkortning")
        if party in votes:
            votes[party] = int(row.get(field) or 0)
    return votes


def historic_profile(votes: dict[str, int], valid: int) -> str:
    if not valid:
        return "Blandat"
    shares = {party: votes.get(party, 0) / valid * 100 for party in PARTY_META}
    if shares["C"] >= 13:
        return "C-starkt"
    if shares["V"] + shares["MP"] >= 20:
        return "V-MP-starkt"
    if shares["SD"] >= 24:
        return "SD-starkt"
    if shares["M"] >= 24:
        return "M-starkt"
    if shares["S"] >= 36:
        return "S-starkt"
    return "Blandat"


def normalize_area(raw_area: dict, metadata: dict, position: int) -> dict | None:
    votes_section = (raw_area.get("rostfordelning") or {}).get("rosterPaverkaMandat") or {}
    valid_current = int(votes_section.get("antalRoster") or 0)
    valid_previous = int(votes_section.get("antalRosterForegaendeVal") or 0)
    if valid_previous <= 0:
        return None

    municipality_code = str(raw_area.get("kommunkod") or "").zfill(4)
    district_code = str(raw_area.get("valdistriktskod") or "")
    previous_code = str(raw_area.get("valdistriktskodForegaendeVal") or "")
    municipality_meta = metadata["by_municipality"].get(
        municipality_code,
        {
            "municipality": municipality_code,
            "county": COUNTY_NAMES.get(municipality_code[:2], municipality_code[:2]),
            "constituency": COUNTY_NAMES.get(municipality_code[:2], municipality_code[:2]),
            "municipalityGroupCode": "NA",
            "municipalityBand": "Okänd kommuntyp",
            "municipalityType": "Okänd kommuntyp",
        },
    )
    district_meta = metadata["by_district"].get(district_code) or metadata["by_district"].get(previous_code) or {}
    votes_previous = party_votes(votes_section, "antalRosterForegaendeVal")
    votes_current = party_votes(votes_section, "antalRoster")
    is_remainder = raw_area.get("statusJamforelse") == "Jämförs mot summerat"
    return {
        "id": district_code or f"{municipality_code}-{position}",
        "kind": "kommunrest" if is_remainder else "valdistrikt",
        "name": raw_area.get("namn") or district_meta.get("name") or district_code,
        "municipality": municipality_meta["municipality"],
        "municipalityCode": municipality_code,
        "countyCode": str(raw_area.get("lankod") or municipality_code[:2]).zfill(2),
        "county": municipality_meta["county"],
        "constituency": raw_area.get("kommunvalkretsNamn") or municipality_meta["constituency"],
        "electorate": int(raw_area.get("antalRostberattigade") or 0),
        "valid22": valid_current,
        "votes22": votes_current,
        "valid18": valid_previous,
        "votes18": votes_previous,
        "reportingTimeRD": raw_area.get("rapporteringsTid"),
        "physicalReplayOrder": position,
        "replayOrder": position,
        "statusJamforelse": raw_area.get("statusJamforelse"),
        "municipalityGroupCode": municipality_meta["municipalityGroupCode"],
        "municipalityBand": municipality_meta["municipalityBand"],
        "municipalityType": municipality_meta["municipalityType"],
        "historicProfile": historic_profile(votes_previous, valid_previous),
    }


def normalize_valmyndigheten_json(
    raw: dict,
    source_name: str,
    checksum: str | None = None,
    config: dict | None = None,
    base_dir: Path | None = None,
) -> tuple[dict, dict]:
    metadata = load_baseline_metadata(config or {}, base_dir or Path.cwd())
    normalized_areas = [
        area
        for position, raw_area in enumerate(raw.get("valdistrikt") or [])
        if (area := normalize_area(raw_area, metadata, position)) is not None
    ]
    reported_areas = [area for area in normalized_areas if area.get("reportingTimeRD")]
    payload = {
        "schema": "vallabbet-live-current-v1",
        "mode": "valmyndigheten-live",
        "election": "RD",
        "year": int(str(raw.get("valdatum") or "2026")[:4]),
        "generatedAt": utc_now(),
        "sourceUpdatedAt": raw.get("senasteUppdateringstid"),
        "source": source_name,
        "sourceChecksum": checksum,
        "adapterStatus": "normalized-valmyndigheten-2026",
        "parties": PARTY_META,
        "districts": normalized_areas,
        "counts": {
            "reportedAreas": len(reported_areas),
            "modelAreas": len(normalized_areas),
            "validReportedVotes": sum(area["valid22"] for area in reported_areas),
            "rawDistricts": len(raw.get("valdistrikt") or []),
            "rawReportedDistricts": raw.get("antalValdistriktRaknade"),
            "rawTotalDistricts": raw.get("antalValdistriktSomSkaRaknas"),
        },
    }
    status = {
        "ok": True,
        "mode": "valmyndigheten-live",
        "updatedAt": utc_now(),
        "sourceUpdatedAt": raw.get("senasteUppdateringstid"),
        "source": source_name,
        "sourceChecksum": checksum,
        "reportedAreas": len(reported_areas),
        "modelAreas": len(normalized_areas),
        "validReportedVotes": payload["counts"]["validReportedVotes"],
        "message": "Fetched and normalized Valmyndigheten JSON.",
    }
    return payload, status


def local_zip_payload(config: dict, base_dir: Path) -> tuple[dict, dict]:
    zip_path = resolve(base_dir, config["localZipFile"])
    data = zip_path.read_bytes()
    checksum = sha256_bytes(data)
    with zipfile.ZipFile(zip_path) as archive:
        member = find_member(archive, config["resultJsonPattern"])
        raw = json.loads(archive.read(member).decode("utf-8-sig"))
    return normalize_valmyndigheten_json(raw, f"local-zip:{zip_path.name}!{member}", checksum, config, base_dir)


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        return response.read()


def parse_md5_index(text: str, zip_pattern: str) -> tuple[str, str] | None:
    for line in text.splitlines():
        if zip_pattern not in line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            checksum = parts[0]
            filename = parts[-1].lstrip("*./")
            return checksum, filename
    return None


def valmyndigheten_url_payload(config: dict, base_dir: Path) -> tuple[dict | None, dict]:
    state_path = resolve(base_dir, config["stateFile"])
    state = read_state(state_path)
    base_url = config["valmyndighetenBaseUrl"].rstrip("/")
    index_url = f"{base_url}/{config['indexFile']}"
    index_text = fetch_bytes(index_url).decode("utf-8", errors="replace")
    found = parse_md5_index(index_text, config["resultZipPattern"])
    if not found:
        raise ValueError(f"Could not find {config['resultZipPattern']} in {index_url}")
    md5_checksum, zip_name = found
    if state.get("lastMd5") == md5_checksum:
        return None, {
            "ok": True,
            "mode": "valmyndigheten-url",
            "updatedAt": utc_now(),
            "source": zip_name,
            "sourceChecksum": md5_checksum,
            "changed": False,
            "message": "No changed Valmyndigheten zip according to index.md5.",
        }

    zip_url = f"{base_url}/{zip_name}"
    data = fetch_bytes(zip_url, timeout=60)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        member = find_member(archive, config["resultJsonPattern"])
        raw = json.loads(archive.read(member).decode("utf-8-sig"))
    payload, status = normalize_valmyndigheten_json(raw, f"{zip_url}!{member}", md5_checksum, config, base_dir)
    status["changed"] = True
    state_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(state_path, {"lastMd5": md5_checksum, "lastZip": zip_name, "updatedAt": utc_now()})
    return payload, status


def run_once(config: dict, base_dir: Path) -> dict:
    public_dir = resolve(base_dir, config["publicDir"])
    snapshot_dir = resolve(base_dir, config["snapshotDir"])
    source = config["source"]
    if source == "fake-2022":
        payload, status = fake_2022_payload(config, base_dir)
    elif source == "local-zip":
        payload, status = local_zip_payload(config, base_dir)
    elif source == "valmyndigheten-url":
        payload, status = valmyndigheten_url_payload(config, base_dir)
        if payload is None:
            write_status(public_dir, status)
            return status
    else:
        raise ValueError(f"Unknown source mode: {source}")

    write_json_atomic(public_dir / "current-riksdag.json", payload)
    if config.get("saveSnapshots", True):
        snapshot = save_snapshot(snapshot_dir, payload, "current-riksdag")
        try:
            status["snapshot"] = str(snapshot.relative_to(base_dir.parent)).replace("\\", "/")
        except ValueError:
            status["snapshot"] = snapshot.name
    write_status(public_dir, status)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch or simulate Vallabbet live data files.")
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.resolve()
    config_path = resolve(base_dir, args.config)
    config = load_json(config_path)
    while True:
        try:
            status = run_once(config, base_dir)
            print(json.dumps(status, ensure_ascii=False, indent=2))
        except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            public_dir = resolve(base_dir, config["publicDir"])
            status = {
                "ok": False,
                "mode": config.get("source"),
                "updatedAt": utc_now(),
                "message": str(exc),
            }
            write_status(public_dir, status)
            print(json.dumps(status, ensure_ascii=False, indent=2), file=sys.stderr)
            if args.once:
                return 1
        if args.once:
            return 0
        time.sleep(int(config.get("pollSeconds", 30)))


if __name__ == "__main__":
    raise SystemExit(main())


