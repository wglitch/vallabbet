from __future__ import annotations

import json
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd


ROOT = Path(__file__).parent
DOWNLOADS = Path.home() / "Downloads"
CACHE = ROOT / ".cache" / "historical"

PARTIES = ["M", "C", "L", "KD", "S", "V", "MP", "SD"]
CHECK_TIMES = ["21:00", "21:15", "21:30", "22:00", "22:30", "23:00", "00:00"]
CHECKPOINTS = [1, 5, 10, 18, 30, 50, 75, 100]
NEIGHBOR_MIN_AREAS = 8
NEIGHBOR_MIN_VOTES = 6500

RESULT_URLS = {
    2010: "https://historik.val.se/val/val2010/statistik/slutligt_valresultat_valdistrikt_R.skv",
    2014: "https://historik.val.se/val/val2014/statistik/2014_riksdagsval_per_valdistrikt.skv",
}

TIMING_FILES = {
    2002: DOWNLOADS / "val2002.xlsx",
    2006: DOWNLOADS / "val2006.xlsx",
    2010: DOWNLOADS / "val2010.xlsx",
    2014: DOWNLOADS / "val2014.xlsx",
    2018: DOWNLOADS / "val2018 inrapporteringstider.xlsx",
    2022: ROOT / "val2022-inrapporteringstider.xlsx",
}

RESULT_FILES = {
    2014: CACHE / "2014_riksdagsval_per_valdistrikt.skv",
    2018: ROOT / "2018_R_per_valdistrikt.xlsx",
    2022: ROOT / "preliminart-roster-per-distrikt-riksdagsvalet-2022.xlsx",
}

MAPPING_FILES = {
    (2014, 2018): DOWNLOADS / "mappning_2014_2018.zip",
    (2018, 2022): ROOT / "jamforelser-2018-2022.xlsx",
}


@dataclass(frozen=True)
class ElectionPair:
    previous: int
    current: int


PAIRS = [
    ElectionPair(2002, 2006),
    ElectionPair(2006, 2010),
    ElectionPair(2010, 2014),
    ElectionPair(2014, 2018),
    ElectionPair(2018, 2022),
]


def number(value) -> int:
    if pd.isna(value):
        return 0
    text = str(value).strip().replace(" ", "").replace(",", ".")
    if not text:
        return 0
    return int(float(text))


def code_parts(county, municipality, district) -> str:
    return f"{number(county):02d}{number(municipality):02d}{number(district):04d}"


def municipality_code(code: str) -> str:
    return code[:4]


def county_code(code: str) -> str:
    return code[:2]


def download_if_needed(year: int) -> None:
    if year not in RESULT_URLS:
        return
    target = RESULT_FILES[year]
    if target.exists():
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    urlretrieve(RESULT_URLS[year], target)


def load_result(year: int) -> dict[str, dict]:
    download_if_needed(year)
    if year == 2018:
        return load_2018_result(RESULT_FILES[year])
    if year == 2014:
        return load_2014_result(RESULT_FILES[year])
    raise ValueError(f"No result loader configured for {year}")


def load_2018_result(path: Path) -> dict[str, dict]:
    source = pd.read_excel(path, sheet_name="R antal").fillna(0)
    rows = {}
    for _, row in source.iterrows():
        code = code_parts(row["LÄNSKOD"], row["KOMMUNKOD"], row["VALDISTRIKTSKOD"])
        if code.endswith("0000"):
            continue
        rows[code] = {
            "id": code,
            "countyCode": county_code(code),
            "municipalityCode": municipality_code(code),
            "county": str(row["LÄNSNAMN"]),
            "municipality": str(row["KOMMUNNAMN"]),
            "name": str(row["VALDISTRIKTSNAMN"]),
            "valid": number(row["RÖSTER GILTIGA"]),
            "votes": {party: number(row.get(party, 0)) for party in PARTIES},
        }
    return rows


def load_2014_result(path: Path) -> dict[str, dict]:
    source = pd.read_csv(path, sep=";", encoding="latin-1", dtype=str).fillna("0")
    rows = {}
    for _, row in source.iterrows():
        code = code_parts(row["LAN"], row["KOM"], row["VALDIST"])
        if code.endswith("0000"):
            continue
        rows[code] = {
            "id": code,
            "countyCode": county_code(code),
            "municipalityCode": municipality_code(code),
            "county": str(row["RIKSDAGSVALKRETS"]),
            "municipality": str(row["KOMMUN"]),
            "name": str(row["Valdistrikt"]),
            "valid": number(row["Rost Giltiga"]),
            "votes": {
                "M": number(row.get("M tal", 0)),
                "C": number(row.get("C tal", 0)),
                "L": number(row.get("FP tal", 0)),
                "KD": number(row.get("KD tal", 0)),
                "S": number(row.get("S tal", 0)),
                "V": number(row.get("V tal", 0)),
                "MP": number(row.get("MP tal", 0)),
                "SD": number(row.get("SD tal", 0)),
            },
        }
    return rows


def load_timing(year: int) -> dict[str, pd.Timestamp]:
    path = TIMING_FILES[year]
    if not path.exists():
        return {}
    source = pd.read_excel(path, dtype=str)
    if year == 2018:
        codes = source.apply(lambda row: code_parts(row.iloc[0], row.iloc[1], row.iloc[2]), axis=1)
        times = pd.to_datetime(source.iloc[:, 6], errors="coerce")
    elif year == 2022:
        codes = source["DISTRIKTKOD"].map(lambda value: f"{number(value):08d}")
        times = pd.to_datetime(source["TID_RD"], errors="coerce")
    else:
        codes = source["VALDISTR"].map(lambda value: f"{number(value):08d}")
        times = pd.to_datetime(source["R_TID"], errors="coerce")
    return {
        code: time
        for code, time in zip(codes, times)
        if pd.notna(time)
    }


def load_municipality_groups() -> dict[str, dict]:
    source = pd.read_excel(
        ROOT / "kommungruppsindelning-2023.xlsx",
        sheet_name="Bilaga1 Lista alla kommuner",
        skiprows=1,
    )
    source.columns = ["groupCode", "municipalityCode", "municipalityName", "mainGroup", "group"]
    return {
        str(row["municipalityCode"]).zfill(4): {
            "municipalityGroupCode": str(row["groupCode"]),
            "municipalityBand": str(row["mainGroup"]),
            "municipalityType": str(row["group"]),
        }
        for _, row in source.iterrows()
    }


def historic_profile(area: dict, baseline_key: str = "previous") -> str:
    valid = area[f"valid{baseline_key}"]
    shares = {party: area[f"votes{baseline_key}"][party] / valid * 100 for party in PARTIES}
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


def load_mapping_2014_2018() -> tuple[pd.DataFrame, pd.DataFrame]:
    path = MAPPING_FILES[(2014, 2018)]
    with zipfile.ZipFile(path) as archive:
        mapping = pd.read_csv(
            archive.open("vd-mappning-2014-2018.skv"),
            sep=";",
            comment="#",
            names=["old", "new", "pct"],
            dtype={"old": str, "new": str},
            encoding="latin-1",
        )
        indelning = pd.read_csv(
            archive.open("vd-indelning-2018.skv"),
            sep=";",
            comment="#",
            names=["code", "kind"],
            dtype=str,
            encoding="latin-1",
        )
    return mapping, indelning


def sum_results(results: list[dict]) -> dict:
    return {
        "valid": sum(row["valid"] for row in results),
        "votes": {party: sum(row["votes"][party] for row in results) for party in PARTIES},
    }


def subtract_results(total: dict, used: dict) -> dict:
    return {
        "valid": total["valid"] - used.get("valid", 0),
        "votes": {
            party: total["votes"][party] - used.get("votes", {}).get(party, 0)
            for party in PARTIES
        },
    }


def build_2018_2014_areas() -> tuple[list[dict], list[dict], dict]:
    current = load_result(2018)
    previous = load_result(2014)
    timing = load_timing(2018)
    municipality_groups = load_municipality_groups()
    mapping, indelning = load_mapping_2014_2018()
    comparable_kinds = set(indelning[indelning["kind"].isin(["O", "S"])]["code"])
    previous_by_current = defaultdict(list)
    for _, row in mapping.iterrows():
        previous_by_current[str(row["new"])].append(str(row["old"]))

    comparable = []
    used_current = set()
    used_previous_by_municipality = defaultdict(lambda: {"valid": 0, "votes": {party: 0 for party in PARTIES}})
    for current_code in sorted(set(current) & comparable_kinds):
        old_codes = previous_by_current.get(current_code, [current_code])
        previous_rows = [previous[code] for code in old_codes if code in previous]
        if not previous_rows or current_code not in timing:
            continue
        baseline = sum_results(previous_rows)
        now = current[current_code]
        area = {
            "id": current_code,
            "kind": "valdistrikt",
            "name": now["name"],
            "county": now["county"],
            "countyCode": now["countyCode"],
            "municipality": now["municipality"],
            "municipalityCode": now["municipalityCode"],
            "validprevious": baseline["valid"],
            "votesprevious": baseline["votes"],
            "validcurrent": now["valid"],
            "votescurrent": now["votes"],
            "reportingTime": timing[current_code],
        }
        area.update(municipality_groups.get(area["municipalityCode"], fallback_group()))
        area["historicProfile"] = historic_profile(area)
        comparable.append(area)
        used_current.add(current_code)
        used = used_previous_by_municipality[area["municipalityCode"]]
        used["valid"] += baseline["valid"]
        for party in PARTIES:
            used["votes"][party] += baseline["votes"][party]

    current_not_used = [row for code, row in current.items() if code not in used_current and code in timing]
    previous_by_municipality = aggregate_by_municipality(previous.values())
    current_components = defaultdict(list)
    for row in current_not_used:
        current_components[row["municipalityCode"]].append(row)

    remainders = []
    for code, components in current_components.items():
        if code not in previous_by_municipality:
            continue
        baseline = subtract_results(previous_by_municipality[code], used_previous_by_municipality[code])
        if baseline["valid"] <= 0 or any(votes < 0 for votes in baseline["votes"].values()):
            continue
        now = sum_results(components)
        if now["valid"] <= 0:
            continue
        area = {
            "id": f"kommunrest-{code}",
            "kind": "kommunrest",
            "name": f"{components[0]['municipality']} kommunrest",
            "county": components[0]["county"],
            "countyCode": components[0]["countyCode"],
            "municipality": components[0]["municipality"],
            "municipalityCode": code,
            "validprevious": baseline["valid"],
            "votesprevious": baseline["votes"],
            "validcurrent": now["valid"],
            "votescurrent": now["votes"],
            "componentDistricts": len(components),
            "reportingTime": max(timing[item["id"]] for item in components),
        }
        area.update(municipality_groups.get(code, fallback_group()))
        area["historicProfile"] = historic_profile(area)
        remainders.append(area)

    all_areas = [*comparable, *remainders]
    all_areas.sort(key=lambda item: (item["reportingTime"], item["kind"], item["id"]))
    for position, area in enumerate(all_areas, start=1):
        area["completeAt"] = position

    diagnostics = {
        "current_districts": len(current),
        "current_with_timing": len(set(current) & set(timing)),
        "previous_districts": len(previous),
        "mapping_rows": len(mapping),
        "mapping_current_codes": mapping["new"].nunique(),
        "comparable_districts": len(comparable),
        "municipality_remainders": len(remainders),
        "model_areas": len(all_areas),
        "target_votes": sum(row["valid"] for row in current.values() if row["id"] in timing),
        "model_votes": sum(area["validcurrent"] for area in all_areas),
    }
    return all_areas, [row for row in current.values() if row["id"] in timing], diagnostics


def fallback_group() -> dict:
    return {
        "municipalityGroupCode": "NA",
        "municipalityBand": "Okänd kommuntyp",
        "municipalityType": "Okänd kommuntyp",
    }


def aggregate_by_municipality(rows) -> dict[str, dict]:
    grouped = defaultdict(lambda: {"valid": 0, "votes": {party: 0 for party in PARTIES}})
    for row in rows:
        bucket = grouped[row["municipalityCode"]]
        bucket["valid"] += row["valid"]
        for party in PARTIES:
            bucket["votes"][party] += row["votes"][party]
    return dict(grouped)


def total(areas: list[dict], suffix: str) -> dict[str, float]:
    return {
        "valid": sum(area[f"valid{suffix}"] for area in areas),
        **{
            party: sum(area[f"votes{suffix}"][party] for area in areas)
            for party in PARTIES
        },
    }


def share(result: dict[str, float], party: str) -> float:
    return result[party] / result["valid"] * 100 if result["valid"] else 0


def swing(current: dict[str, float], baseline: dict[str, float], party: str) -> float:
    return share(current, party) - share(baseline, party)


def raw_share(counted: list[dict]) -> dict[str, float]:
    counted_now = total(counted, "current")
    return {party: share(counted_now, party) for party in PARTIES}


def baseline_share(areas: list[dict]) -> dict[str, float]:
    baseline = total(areas, "previous")
    return {party: share(baseline, party) for party in PARTIES}


def target_share(target_rows: list[dict]) -> dict[str, float]:
    summed = sum_results(target_rows)
    return {party: share({**summed["votes"], "valid": summed["valid"]}, party) for party in PARTIES}


def stats_for(counted: list[dict]) -> dict[str, dict]:
    layers = forecast_layers()
    groups = defaultdict(list)
    for _, key, _, _ in layers:
        for area in counted:
            groups[key(area)].append(area)
    return {
        key: {
            "districts": len(group),
            "current": total(group, "current"),
            "baseline": total(group, "previous"),
        }
        for key, group in groups.items()
    }


def forecast_layers():
    return [
        ("kommuntyp + profil", lambda d: f"type-profile:{d['municipalityType']}|{d['historicProfile']}", 8, 6500),
        ("kommuntyp", lambda d: f"type:{d['municipalityType']}", 16, 12000),
        ("huvudgrupp + profil", lambda d: f"band-profile:{d['municipalityBand']}|{d['historicProfile']}", 10, 8500),
        ("huvudgrupp", lambda d: f"band:{d['municipalityBand']}", 22, 18000),
        ("historisk profil", lambda d: f"profile:{d['historicProfile']}", 20, 16000),
        ("län", lambda d: f"county:{d['countyCode']}", 18, 12000),
        ("riket", lambda _: "national", 1, 1),
    ]


def choose(stats: dict[str, dict], area: dict) -> dict:
    for _, key, min_areas, min_votes in forecast_layers():
        stat = stats.get(key(area))
        if stat and stat["districts"] >= min_areas and stat["baseline"]["valid"] >= min_votes:
            return stat
    return stats["national"]


def adjusted_forecast(counted: list[dict], uncounted: list[dict]) -> dict[str, float]:
    if not counted:
        return baseline_share(uncounted)
    stats = stats_for(counted)
    counted_now = total(counted, "current")
    votes = {party: counted_now[party] for party in PARTIES}
    valid = counted_now["valid"] + total(uncounted, "previous")["valid"]
    for area in uncounted:
        stat = choose(stats, area)
        for party in PARTIES:
            base = area["votesprevious"][party] / area["validprevious"] * 100
            delta = swing(stat["current"], stat["baseline"], party)
            votes[party] += max(0, base + delta) / 100 * area["validprevious"]
    return {party: votes[party] / valid * 100 for party in PARTIES}


def national_forecast(counted: list[dict], uncounted: list[dict]) -> dict[str, float]:
    if not counted:
        return baseline_share(uncounted)
    counted_now = total(counted, "current")
    counted_base = total(counted, "previous")
    uncounted_base = total(uncounted, "previous")
    valid = counted_now["valid"] + uncounted_base["valid"]
    return {
        party: (
            counted_now[party]
            + max(0, share(uncounted_base, party) + swing(counted_now, counted_base, party))
            / 100
            * uncounted_base["valid"]
        )
        / valid
        * 100
        for party in PARTIES
    }


def neighbor_keys(area: dict) -> list[str]:
    return [
        f"municipality:{area['municipalityCode']}",
        f"county-type-profile:{area['countyCode']}|{area['municipalityType']}|{area['historicProfile']}",
        f"county-type:{area['countyCode']}|{area['municipalityType']}",
        f"county-profile:{area['countyCode']}|{area['historicProfile']}",
        f"county:{area['countyCode']}",
        f"type-profile:{area['municipalityType']}|{area['historicProfile']}",
        "national",
    ]


def neighbor_stats(counted: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for area in counted:
        for key in neighbor_keys(area):
            groups[key].append(area)
    return {
        key: {
            "districts": len(group),
            "current": total(group, "current"),
            "baseline": total(group, "previous"),
        }
        for key, group in groups.items()
    }


def choose_neighbor(stats: dict[str, dict], area: dict) -> dict:
    for key in neighbor_keys(area):
        stat = stats.get(key)
        if stat and stat["districts"] >= NEIGHBOR_MIN_AREAS and stat["baseline"]["valid"] >= NEIGHBOR_MIN_VOTES:
            return stat
    return stats["national"]


def neighbor_forecast(counted: list[dict], uncounted: list[dict]) -> dict[str, float]:
    if not counted:
        return baseline_share(uncounted)
    stats = neighbor_stats(counted)
    counted_now = total(counted, "current")
    votes = {party: counted_now[party] for party in PARTIES}
    valid = counted_now["valid"] + total(uncounted, "previous")["valid"]
    for area in uncounted:
        stat = choose_neighbor(stats, area)
        for party in PARTIES:
            base = area["votesprevious"][party] / area["validprevious"] * 100
            delta = swing(stat["current"], stat["baseline"], party)
            votes[party] += max(0, base + delta) / 100 * area["validprevious"]
    return {party: votes[party] / valid * 100 for party in PARTIES}


def neighbor_blend_weight(current_votes: float, uncounted_votes: float) -> float:
    if not uncounted_votes:
        return 0
    if current_votes >= 2_500_000:
        return .6
    if current_votes >= 1_500_000:
        return .35
    if current_votes >= 900_000:
        return .15
    return 0


def hybrid_forecast(counted: list[dict], uncounted: list[dict]) -> dict[str, float]:
    adjusted = adjusted_forecast(counted, uncounted)
    neighbor = neighbor_forecast(counted, uncounted)
    counted_now = total(counted, "current")
    uncounted_base = total(uncounted, "previous")
    weight = neighbor_blend_weight(counted_now["valid"], uncounted_base["valid"])
    return {
        party: adjusted[party] * (1 - weight) + neighbor[party] * weight
        for party in PARTIES
    }


def mae(estimate: dict[str, float], target: dict[str, float]) -> float:
    return sum(abs(estimate[party] - target[party]) for party in PARTIES) / len(PARTIES)


def areas_at_time(areas: list[dict], when: pd.Timestamp) -> tuple[list[dict], list[dict]]:
    counted = [area for area in areas if area["reportingTime"] <= when]
    return counted, [area for area in areas if area not in counted]


def areas_at_checkpoint(areas: list[dict], checkpoint: int) -> tuple[list[dict], list[dict]]:
    position = max(1, round(len(areas) * checkpoint / 100))
    return areas[:position], areas[position:]


def election_date_from_areas(areas: list[dict]) -> pd.Timestamp:
    return min(area["reportingTime"] for area in areas).normalize()


def clock_time(base_day: pd.Timestamp, clock: str) -> pd.Timestamp:
    hour, minute = [int(part) for part in clock.split(":")]
    when = base_day + pd.Timedelta(hours=hour, minutes=minute)
    if hour < 12:
        when += pd.Timedelta(days=1)
    return when


def result_available(year: int) -> bool:
    path = RESULT_FILES.get(year)
    return bool((path and path.exists()) or year in RESULT_URLS)


def mapping_available(pair: ElectionPair) -> bool:
    path = MAPPING_FILES.get((pair.previous, pair.current))
    return bool(path and path.exists())


def write_report() -> None:
    areas, target_rows, diagnostics = build_2018_2014_areas()
    target = target_share(target_rows)
    first_day = election_date_from_areas(areas)
    lines = [
        "# Historical Preflight",
        "",
        "Purpose: check whether older election pairs can be used for model evaluation before changing the live prototype pipeline.",
        "",
        "## Pair Availability",
        "",
        "| Pair | Current timing file | Previous result | Current result | Mapping | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for pair in PAIRS:
        timing_path = TIMING_FILES.get(pair.current)
        timing = "yes" if timing_path and timing_path.exists() else "missing"
        previous = "yes" if result_available(pair.previous) else "missing"
        current = "yes" if result_available(pair.current) else "missing"
        mapping = "yes" if mapping_available(pair) else "missing"
        status = "ready" if pair == ElectionPair(2014, 2018) else "needs adapter/data"
        lines.append(f"| {pair.current} vs {pair.previous} | {timing} | {previous} | {current} | {mapping} | {status} |")

    lines.extend([
        "",
        "## 2018 vs 2014 Data Coverage",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ])
    for key, value in diagnostics.items():
        if key.endswith("_votes"):
            lines.append(f"| {key.replace('_', ' ')} | {value:,} |")
        else:
            lines.append(f"| {key.replace('_', ' ')} | {value:,} |")
    coverage = diagnostics["model_votes"] / diagnostics["target_votes"] * 100 if diagnostics["target_votes"] else 0
    lines.append(f"| model vote coverage | {coverage:.2f}% |")

    lines.extend([
        "",
        "## 2018 vs 2014 Clock-Time Backtest",
        "",
        "Target is final 2018 district result for districts with reporting time. This is a historical proxy, not a preserved 2018 val-night snapshot.",
        "",
        "| Time | Model areas counted | Counted votes | Raw MAE | National MAE | Adjusted MAE | Local-neighbor MAE | Hybrid UI MAE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for clock in CHECK_TIMES:
        when = clock_time(first_day, clock)
        counted, uncounted = areas_at_time(areas, when)
        counted_votes = total(counted, "current")["valid"]
        lines.append(
            f"| {clock} | {len(counted):,} | {counted_votes:,.0f} | "
            f"{mae(raw_share(counted), target):.2f} | "
            f"{mae(national_forecast(counted, uncounted), target):.2f} | "
            f"{mae(adjusted_forecast(counted, uncounted), target):.2f} | "
            f"{mae(neighbor_forecast(counted, uncounted), target):.2f} | "
            f"{mae(hybrid_forecast(counted, uncounted), target):.2f} |"
        )

    lines.extend([
        "",
        "## 2018 vs 2014 Model-Area Checkpoints",
        "",
        "| Counted model areas | Raw MAE | National MAE | Adjusted MAE | Local-neighbor MAE | Hybrid UI MAE |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for checkpoint in CHECKPOINTS:
        counted, uncounted = areas_at_checkpoint(areas, checkpoint)
        lines.append(
            f"| {checkpoint}% | "
            f"{mae(raw_share(counted), target):.2f} | "
            f"{mae(national_forecast(counted, uncounted), target):.2f} | "
            f"{mae(adjusted_forecast(counted, uncounted), target):.2f} | "
            f"{mae(neighbor_forecast(counted, uncounted), target):.2f} | "
            f"{mae(hybrid_forecast(counted, uncounted), target):.2f} |"
        )

    lines.extend([
        "",
        "## Party-Level Absolute Errors at 2018 Clock Times",
        "",
        "| Time | " + " | ".join(PARTIES) + " |",
        "| --- | " + " | ".join("---:" for _ in PARTIES) + " |",
    ])
    for clock in CHECK_TIMES:
        when = clock_time(first_day, clock)
        counted, uncounted = areas_at_time(areas, when)
        forecast = hybrid_forecast(counted, uncounted)
        errors = {party: abs(forecast[party] - target[party]) for party in PARTIES}
        lines.append("| " + clock + " | " + " | ".join(f"{errors[party]:.2f}" for party in PARTIES) + " |")

    lines.extend([
        "",
        "## Next Fixes Before The Full Series",
        "",
        "1. Add result loaders for 2002, 2006 and 2010.",
        "2. Locate or reconstruct district comparison mappings for 2002/2006, 2006/2010 and 2010/2014.",
        "3. Decide whether older tests should target final results, val-night XML snapshots, or both.",
        "4. Replace this pair-specific script with a parameterized historical backtest module once at least two pairs run cleanly.",
    ])
    (ROOT / "historical-preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    print("Wrote historical-preflight.md")


if __name__ == "__main__":
    write_report()
