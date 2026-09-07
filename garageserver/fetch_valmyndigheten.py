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


def normalize_valmyndigheten_json(raw: dict, source_name: str, checksum: str | None = None) -> tuple[dict, dict]:
    payload = {
        "schema": "vallabbet-live-current-v1",
        "mode": "valmyndigheten-json",
        "election": "RD",
        "year": 2026,
        "generatedAt": utc_now(),
        "source": source_name,
        "sourceChecksum": checksum,
        "adapterStatus": "raw-stored-schema-pending",
        "counts": {},
        "areas": [],
        "raw": raw,
    }
    status = {
        "ok": True,
        "mode": "valmyndigheten-json",
        "updatedAt": utc_now(),
        "source": source_name,
        "sourceChecksum": checksum,
        "message": "Fetched Valmyndigheten JSON. Exact 2026 schema adapter still needs validation against sample files.",
    }
    return payload, status


def local_zip_payload(config: dict, base_dir: Path) -> tuple[dict, dict]:
    zip_path = resolve(base_dir, config["localZipFile"])
    data = zip_path.read_bytes()
    checksum = sha256_bytes(data)
    with zipfile.ZipFile(zip_path) as archive:
        member = find_member(archive, config["resultJsonPattern"])
        raw = json.loads(archive.read(member).decode("utf-8-sig"))
    return normalize_valmyndigheten_json(raw, f"local-zip:{zip_path.name}!{member}", checksum)


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
    payload, status = normalize_valmyndigheten_json(raw, f"{zip_url}!{member}", md5_checksum)
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


