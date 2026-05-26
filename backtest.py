from __future__ import annotations

import json
import random
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
TIMING_FILE = ROOT / "val2022-inrapporteringstider.xlsx"
PARTY_LABELS = {
    "Moderaterna": "M",
    "Centerpartiet": "C",
    "Liberalerna": "L",
    "Kristdemokraterna": "KD",
    "Socialdemokraterna": "S",
    "Vänsterpartiet": "V",
    "Miljöpartiet": "MP",
    "Sverigedemokraterna": "SD",
}
PARTIES = list(PARTY_LABELS.values())
CHECKPOINTS = [1, 5, 10, 18, 30, 50, 75, 100]
TIME_CHECKPOINTS = [
    "2022-09-11 21:00",
    "2022-09-11 21:15",
    "2022-09-11 21:30",
    "2022-09-11 21:43",
    "2022-09-11 22:16",
    "2022-09-11 22:30",
    "2022-09-11 23:00",
    "2022-09-12 00:00",
]
RANDOM_RUNS = 10
RANDOM_SEED = 20260524
NEIGHBOR_MIN_AREAS = 8
NEIGHBOR_MIN_VOTES = 6500
LAYERS = [
    ("kommuntyp + profil", lambda d: f"type-profile:{d['municipalityType']}|{d['historicProfile']}", 8, 6500),
    ("kommuntyp", lambda d: f"type:{d['municipalityType']}", 16, 12000),
    ("huvudgrupp + profil", lambda d: f"band-profile:{d['municipalityBand']}|{d['historicProfile']}", 10, 8500),
    ("huvudgrupp", lambda d: f"band:{d['municipalityBand']}", 22, 18000),
    ("historisk profil", lambda d: f"profile:{d['historicProfile']}", 20, 16000),
    ("län", lambda d: f"county:{d['county']}", 18, 12000),
    ("riket", lambda _: "national", 1, 1),
]


def total(districts: list[dict], year: str) -> dict[str, float]:
    valid_key = f"valid{year}"
    vote_key = f"votes{year}"
    result = {"valid": sum(district[valid_key] for district in districts)}
    result.update({
        party: sum(district[vote_key][party] for district in districts)
        for party in PARTIES
    })
    return result


def share(result: dict[str, float], party: str) -> float:
    return result[party] / result["valid"] * 100 if result["valid"] else 0


def swing(current: dict[str, float], baseline: dict[str, float], party: str) -> float:
    return share(current, party) - share(baseline, party)


def stats_for(districts: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for _, key, _, _ in LAYERS:
        for district in districts:
            groups[key(district)].append(district)
    return {
        key: {"districts": len(group), "current": total(group, "22"), "baseline": total(group, "18")}
        for key, group in groups.items()
    }


def choose(stats: dict[str, dict], district: dict) -> dict:
    for _, key, min_districts, min_votes in LAYERS:
        stat = stats.get(key(district))
        if stat and stat["districts"] >= min_districts and stat["baseline"]["valid"] >= min_votes:
            return stat
    return stats["national"]


def adjusted_forecast(counted: list[dict], uncounted: list[dict]) -> dict[str, float]:
    stats = stats_for(counted)
    counted_now = total(counted, "22")
    votes = {party: counted_now[party] for party in PARTIES}
    valid = counted_now["valid"] + total(uncounted, "18")["valid"]
    for district in uncounted:
        stat = choose(stats, district)
        for party in PARTIES:
            base = district["votes18"][party] / district["valid18"] * 100
            delta = swing(stat["current"], stat["baseline"], party)
            votes[party] += max(0, base + delta) / 100 * district["valid18"]
    return {party: votes[party] / valid * 100 for party in PARTIES}


def national_forecast(counted: list[dict], uncounted: list[dict]) -> dict[str, float]:
    counted_now = total(counted, "22")
    counted_base = total(counted, "18")
    uncounted_base = total(uncounted, "18")
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


def area_sort_code(area: dict) -> int:
    if str(area["id"]).isdigit():
        return int(area["id"])
    if area.get("municipalityCode", "").isdigit():
        return int(area["municipalityCode"]) * 10000 + 9999
    return 999999999


def area_county_code(area: dict) -> str:
    if area.get("countyCode"):
        return str(area["countyCode"])
    if area.get("municipalityCode") and str(area["municipalityCode"]).isdigit():
        return str(area["municipalityCode"])[:2]
    if str(area.get("id", "")).isdigit():
        return str(area["id"])[:2]
    return str(area.get("county", ""))


def neighbor_bucket(counted: list[dict], area: dict, bucket: int) -> list[dict]:
    county_code = area_county_code(area)
    if bucket == 0:
        return [item for item in counted if item["municipalityCode"] == area["municipalityCode"]]
    if bucket == 1:
        return [
            item for item in counted
            if area_county_code(item) == county_code
            and item["municipalityType"] == area["municipalityType"]
            and item["historicProfile"] == area["historicProfile"]
        ]
    if bucket == 2:
        return [
            item for item in counted
            if area_county_code(item) == county_code
            and item["municipalityType"] == area["municipalityType"]
        ]
    if bucket == 3:
        return [
            item for item in counted
            if area_county_code(item) == county_code
            and item["historicProfile"] == area["historicProfile"]
        ]
    if bucket == 4:
        return [item for item in counted if area_county_code(item) == county_code]
    if bucket == 5:
        return [
            item for item in counted
            if item["municipalityType"] == area["municipalityType"]
            and item["historicProfile"] == area["historicProfile"]
        ]
    return counted


def neighbor_keys(area: dict) -> list[str]:
    county = area_county_code(area)
    return [
        f"municipality:{area['municipalityCode']}",
        f"county-type-profile:{county}|{area['municipalityType']}|{area['historicProfile']}",
        f"county-type:{county}|{area['municipalityType']}",
        f"county-profile:{county}|{area['historicProfile']}",
        f"county:{county}",
        f"type-profile:{area['municipalityType']}|{area['historicProfile']}",
        "national",
    ]


def neighbor_stats(counted: list[dict]) -> dict[str, dict]:
    groups = defaultdict(list)
    for area in counted:
        for key in neighbor_keys(area):
            groups[key].append(area)
    return {
        key: {"districts": len(group), "current": total(group, "22"), "baseline": total(group, "18")}
        for key, group in groups.items()
    }


def choose_neighbor_stat(stats: dict[str, dict], area: dict) -> dict:
    for key in neighbor_keys(area):
        stat = stats.get(key)
        if stat and stat["districts"] >= NEIGHBOR_MIN_AREAS and stat["baseline"]["valid"] >= NEIGHBOR_MIN_VOTES:
            return stat
    return stats["national"]


def neighbor_forecast(counted: list[dict], uncounted: list[dict]) -> dict[str, float]:
    stats = neighbor_stats(counted)
    counted_now = total(counted, "22")
    votes = {party: counted_now[party] for party in PARTIES}
    valid = counted_now["valid"] + total(uncounted, "18")["valid"]
    for area in uncounted:
        stat = choose_neighbor_stat(stats, area)
        for party in PARTIES:
            base = area["votes18"][party] / area["valid18"] * 100
            delta = swing(stat["current"], stat["baseline"], party)
            votes[party] += max(0, base + delta) / 100 * area["valid18"]
    return {party: votes[party] / valid * 100 for party in PARTIES}


def raw_share(counted: list[dict]) -> dict[str, float]:
    counted_now = total(counted, "22")
    return {party: share(counted_now, party) for party in PARTIES}


def mae(estimate: dict[str, float], target: dict[str, float]) -> float:
    return sum(abs(estimate[party] - target[party]) for party in PARTIES) / len(PARTIES)


@lru_cache(maxsize=1)
def load_reporting_times() -> dict[int, pd.Timestamp]:
    if not TIMING_FILE.exists():
        return {}
    source = pd.read_excel(TIMING_FILE)
    source["code"] = source["DISTRIKTKOD"].astype(int)
    source["time"] = pd.to_datetime(source["TID_RD"], errors="coerce")
    return {
        int(row["code"]): row["time"]
        for _, row in source.dropna(subset=["time"]).iterrows()
    }


def election_night_target() -> dict[str, float]:
    source = pd.read_excel(ROOT / "preliminart-roster-per-distrikt-riksdagsvalet-2022.xlsx")
    source["code"] = source["Distrikt"].map(code_2022).astype(int)
    timing_codes = set(load_reporting_times())
    if timing_codes:
        physical = source[source["code"].isin(timing_codes)]
    else:
        physical = source[source["Kommun"].notna() & ~source["Distrikt"].str.endswith("-0000")]
    totals = physical.groupby("Parti", as_index=True)["Röster"].sum()
    valid = totals["Summa giltiga röster"]
    return {
        short: totals[full_name] / valid * 100
        for full_name, short in PARTY_LABELS.items()
    }


def code_2022(raw_id: str) -> str:
    return raw_id.replace("RD-", "").replace("-", "")


def party_votes(rows: pd.DataFrame, labels: dict[str, str]) -> dict[str, int]:
    indexed = rows.set_index("Parti")
    return {
        short: int(indexed.loc[full_name, "Röster"])
        for full_name, short in labels.items()
    }


def load_physical_2022() -> list[dict]:
    reporting_times = load_reporting_times()
    source = pd.read_excel(ROOT / "preliminart-roster-per-distrikt-riksdagsvalet-2022.xlsx")
    source["code"] = source["Distrikt"].map(code_2022)
    if reporting_times:
        source = source[source["code"].astype(int).isin(reporting_times)].copy()
    else:
        source = source[source["Kommun"].notna() & ~source["Distrikt"].str.endswith("-0000")].copy()
    areas = []
    for code, rows in source.groupby("code", sort=False):
        first = rows.iloc[0]
        indexed = rows.set_index("Parti")
        areas.append({
            "id": code,
            "municipalityCode": code[:4],
            "countyCode": code[:2],
            "county": str(first["Län"]),
            "municipality": str(first["Kommun"]),
            "valid22": int(indexed.loc["Summa giltiga röster", "Röster"]),
            "votes22": party_votes(rows, PARTY_LABELS),
            "reportingTime": reporting_times.get(int(code)),
        })
    if reporting_times:
        areas.sort(key=lambda area: (area["reportingTime"], area["id"]))
    else:
        areas.sort(key=lambda area: (area["valid22"], area["id"]))
    for position, area in enumerate(areas, start=1):
        area["completeAt"] = position
    return areas


@lru_cache(maxsize=1)
def load_physical_2018_by_municipality() -> dict[str, dict]:
    source = pd.read_excel(ROOT / "2018_R_per_valdistrikt.xlsx", sheet_name="R antal").fillna(0)
    source = source[source["VALDISTRIKTSKOD"].ne(0)].copy()
    source["municipalityCode"] = (
        source["LÄNSKOD"].map(lambda value: f"{int(value):02d}")
        + source["KOMMUNKOD"].map(lambda value: f"{int(value):02d}")
    )
    results = {}
    for code, rows in source.groupby("municipalityCode"):
        results[code] = {
            "valid": int(rows["RÖSTER GILTIGA"].sum()),
            **{party: int(rows[party].sum()) for party in PARTIES},
        }
    return results


def subtract(total_result: dict, part_result: dict) -> dict:
    return {
        key: int(total_result.get(key, 0) - part_result.get(key, 0))
        for key in ["valid", *PARTIES]
    }


def aggregate_model_areas(areas: list[dict], year: str) -> dict[str, dict]:
    results = defaultdict(lambda: {"valid": 0, **{party: 0 for party in PARTIES}})
    for area in areas:
        bucket = results[area["municipalityCode"]]
        bucket["valid"] += area[f"valid{year}"]
        for party in PARTIES:
            bucket[party] += area[f"votes{year}"][party]
    return dict(results)


def aggregate_results_by_county(results: dict[str, dict]) -> dict[str, dict]:
    counties = defaultdict(lambda: {"valid": 0, **{party: 0 for party in PARTIES}})
    for municipality, result in results.items():
        bucket = counties[municipality[:2]]
        bucket["valid"] += result["valid"]
        for party in PARTIES:
            bucket[party] += result[party]
    return dict(counties)


def profile_from_result(result: dict[str, int]) -> str:
    shares = {party: result[party] / result["valid"] * 100 for party in PARTIES}
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


@lru_cache(maxsize=1)
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


def sum_area_votes(areas: list[dict], valid_key: str, vote_key: str) -> dict:
    return {
        "valid": sum(area[valid_key] for area in areas),
        **{party: sum(area[vote_key][party] for area in areas) for party in PARTIES},
    }


def remainder_area(
    code: str,
    components: list[dict],
    baseline: dict,
    meta: dict,
    kind: str,
) -> dict | None:
    current = sum_area_votes(components, "valid22", "votes22")
    if current["valid"] <= 0 or baseline["valid"] <= 0:
        return None
    if any(baseline[party] < 0 for party in PARTIES):
        return None
    return {
        "id": f"{kind}:{code}",
        "kind": kind,
        "districts": len(components),
        "municipalityCode": code if kind == "kommunrest" else "NA",
        "countyCode": meta["countyCode"],
        "county": meta["county"],
        "municipality": meta.get("municipality", f"{meta['county']} rest"),
        "municipalityType": meta.get("municipalityType", "Okänd kommuntyp"),
        "municipalityBand": meta.get("municipalityBand", "Okänd kommuntyp"),
        "historicProfile": profile_from_result(baseline),
        "valid18": baseline["valid"],
        "votes18": {party: baseline[party] for party in PARTIES},
        "valid22": current["valid"],
        "votes22": {party: current[party] for party in PARTIES},
        "completeAt": max(component["completeAt"] for component in components),
        "reportingTime": max(
            (component.get("reportingTime") for component in components if component.get("reportingTime")),
            default=None,
        ),
    }


def municipality_remainders(comparable: list[dict], physical22: list[dict]) -> tuple[list[dict], list[dict]]:
    all18 = load_physical_2018_by_municipality()
    municipality_groups = load_municipality_groups()
    comparable18 = aggregate_model_areas(comparable, "18")
    comparable_ids = {int(area["id"]) for area in comparable}
    noncomparable22 = [area for area in physical22 if int(area["id"]) not in comparable_ids]
    components_by_municipality = defaultdict(list)
    for area in noncomparable22:
        components_by_municipality[area["municipalityCode"]].append(area)
    meta_by_municipality = {
        area["municipalityCode"]: area
        for area in [*comparable, *physical22]
    }
    remainders = []
    leftovers = []
    for code, components in components_by_municipality.items():
        if code not in all18:
            leftovers.extend(components)
            continue
        baseline = subtract(all18[code], comparable18.get(code, {}))
        area = remainder_area(code, components, baseline, meta_by_municipality[code], "kommunrest")
        if area:
            area.update(
                municipality_groups.get(
                    code,
                    {
                        "municipalityGroupCode": "NA",
                        "municipalityBand": "OkÃ¤nd kommuntyp",
                        "municipalityType": "OkÃ¤nd kommuntyp",
                    },
                )
            )
            remainders.append(area)
        else:
            leftovers.extend(components)
    return remainders, leftovers


def county_fallback_remainders(leftovers: list[dict], comparable: list[dict], municipality: list[dict]) -> list[dict]:
    all18 = aggregate_results_by_county(load_physical_2018_by_municipality())
    comparable18 = aggregate_results_by_county(aggregate_model_areas(comparable, "18"))
    municipality18 = defaultdict(lambda: {"valid": 0, **{party: 0 for party in PARTIES}})
    for area in municipality:
        bucket = municipality18[area["countyCode"]]
        bucket["valid"] += area["valid18"]
        for party in PARTIES:
            bucket[party] += area["votes18"][party]
    groups = defaultdict(list)
    for area in leftovers:
        groups[area["countyCode"]].append(area)
    remainders = []
    for code, components in groups.items():
        baseline = subtract(subtract(all18.get(code, {}), comparable18.get(code, {})), municipality18.get(code, {}))
        area = remainder_area(code, components, baseline, components[0], "länsrest")
        if area:
            remainders.append(area)
    return remainders


def county_remainders(comparable: list[dict], physical22: list[dict]) -> list[dict]:
    all18 = aggregate_results_by_county(load_physical_2018_by_municipality())
    comparable18 = aggregate_results_by_county(aggregate_model_areas(comparable, "18"))
    comparable_ids = {int(area["id"]) for area in comparable}
    components = defaultdict(list)
    for area in physical22:
        if int(area["id"]) not in comparable_ids:
            components[area["countyCode"]].append(area)
    remainders = []
    for code, county_components in components.items():
        baseline = subtract(all18.get(code, {}), comparable18.get(code, {}))
        area = remainder_area(code, county_components, baseline, county_components[0], "länsrest")
        if area:
            remainders.append(area)
    return remainders


def areas_at_checkpoint(areas: list[dict], checkpoint: int, physical_count: int) -> tuple[list[dict], list[dict]]:
    position = max(1, round(physical_count * checkpoint / 100))
    counted = [area for area in areas if area["completeAt"] <= position]
    uncounted = [area for area in areas if area["completeAt"] > position]
    return counted, uncounted


def areas_at_time(areas: list[dict], when: pd.Timestamp) -> tuple[list[dict], list[dict]]:
    counted = [area for area in areas if area.get("reportingTime") is not None and area["reportingTime"] <= when]
    uncounted = [area for area in areas if area not in counted]
    return counted, uncounted


def attach_complete_positions(districts: list[dict], physical22: list[dict]) -> list[dict]:
    positions = {int(area["id"]): area["completeAt"] for area in physical22}
    times = {int(area["id"]): area.get("reportingTime") for area in physical22}
    positioned = []
    for district in districts:
        current = dict(district)
        current["completeAt"] = positions[int(current["id"])]
        current["reportingTime"] = times.get(int(current["id"]))
        current["kind"] = "valdistrikt"
        positioned.append(current)
    return positioned


def randomized_physical_order(physical22: list[dict], seed: int) -> list[dict]:
    shuffled = [dict(area) for area in physical22]
    random.Random(seed).shuffle(shuffled)
    for position, area in enumerate(shuffled, start=1):
        area["completeAt"] = position
    return shuffled


def model_error(areas: list[dict], checkpoint: int, physical_count: int, target: dict, method) -> float:
    counted, uncounted = areas_at_checkpoint(areas, checkpoint, physical_count)
    return mae(method(counted, uncounted), target)


def model_inputs_for_order(districts: list[dict], physical22: list[dict]) -> dict[str, list[dict]]:
    comparable = attach_complete_positions(districts, physical22)
    municipality, _ = municipality_remainders(comparable, physical22)
    county = county_remainders(comparable, physical22)
    return {
        "comparable": comparable,
        "municipality": [*comparable, *municipality],
        "county": [*comparable, *county],
    }


def random_order_summary(districts: list[dict], base_physical22: list[dict], target: dict) -> list[str]:
    rows = []
    for run in range(1, RANDOM_RUNS + 1):
        seed = RANDOM_SEED + run
        randomized = randomized_physical_order(base_physical22, seed)
        areas = model_inputs_for_order(districts, randomized)["municipality"]
        for checkpoint in CHECKPOINTS:
            counted, uncounted = areas_at_checkpoint(areas, checkpoint, len(randomized))
            rows.append({
                "run": run,
                "seed": seed,
                "checkpoint": checkpoint,
                "areas": len(counted),
                "votes": total(counted, "22")["valid"],
                "raw": mae(raw_share(counted), target),
                "national": mae(national_forecast(counted, uncounted), target),
                "adjusted": mae(adjusted_forecast(counted, uncounted), target),
                "neighbor": mae(neighbor_forecast(counted, uncounted), target),
            })

    lines = [
        "",
        "## Ten random reporting-order simulations",
        "",
        "This is a temporary stress test while the real 2022 reporting order is missing.",
        f"It shuffles physical polling-station districts with seeds `{RANDOM_SEED + 1}` to `{RANDOM_SEED + RANDOM_RUNS}`.",
        "Municipality remainders still become available only when all their component districts have appeared.",
        "Because the order is fully random, this is a friendly lower-bound test, not a realistic election-night test.",
        "Real reporting can be geographically and administratively clustered, which is exactly why the real timestamps still matter.",
        "",
        "Rule of thumb for reading the table: around `<= 1.0` MAE means the forecast is probably useful for the broad trend; around `<= 0.5` is much steadier.",
        "",
        "| Reported physical districts | Median adjusted MAE | Median neighbor MAE | Neighbor wins | Worst neighbor MAE | Runs neighbor <= 1.0 | Runs neighbor <= 0.5 | Median counted votes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    first_good = []
    for checkpoint in CHECKPOINTS:
        subset = [row for row in rows if row["checkpoint"] == checkpoint]
        adjusted = sorted(row["adjusted"] for row in subset)
        neighbor = sorted(row["neighbor"] for row in subset)
        votes = sorted(row["votes"] for row in subset)
        median_adjusted = adjusted[len(adjusted) // 2]
        median_neighbor = neighbor[len(neighbor) // 2]
        median_votes = votes[len(votes) // 2]
        neighbor_wins = sum(row["neighbor"] < row["adjusted"] for row in subset)
        good = sum(value <= 1.0 for value in neighbor)
        steady = sum(value <= .5 for value in neighbor)
        if sum(value <= 1.0 for value in adjusted) == RANDOM_RUNS:
            first_good.append(checkpoint)
        lines.append(
            f"| {checkpoint}% | {median_adjusted:.2f} | {median_neighbor:.2f} | "
            f"{neighbor_wins}/{RANDOM_RUNS} | {max(neighbor):.2f} | "
            f"{good}/{RANDOM_RUNS} | {steady}/{RANDOM_RUNS} | {median_votes:,.0f} |"
        )

    by_run = defaultdict(list)
    for row in rows:
        by_run[row["run"]].append(row)
    lines.extend([
        "",
        "| Random run | First adjusted <= 1.0 MAE | First neighbor <= 1.0 MAE | First neighbor <= 0.5 MAE |",
        "| ---: | ---: | ---: | ---: |",
    ])
    for run, run_rows in sorted(by_run.items()):
        adjusted_good = next((row["checkpoint"] for row in run_rows if row["adjusted"] <= 1.0), None)
        neighbor_good = next((row["checkpoint"] for row in run_rows if row["neighbor"] <= 1.0), None)
        neighbor_steady = next((row["checkpoint"] for row in run_rows if row["neighbor"] <= .5), None)
        lines.append(
            f"| {run} | {adjusted_good if adjusted_good is not None else '-'}% | "
            f"{neighbor_good if neighbor_good is not None else '-'}% | "
            f"{neighbor_steady if neighbor_steady is not None else '-'}% |"
        )

    if first_good:
        lines.extend([
            "",
            f"In these random simulations, every run is below 1.0 MAE from `{first_good[0]}%` reported physical districts.",
        ])
    return lines


def actual_time_summary(areas: list[dict], physical22: list[dict], target: dict) -> list[str]:
    if not TIMING_FILE.exists() or not any(area.get("reportingTime") for area in physical22):
        return []
    gap_start = pd.Timestamp("2022-09-11 21:43")
    gap_end = pd.Timestamp("2022-09-11 22:16")
    before_gap = sum(area["reportingTime"] < gap_start for area in physical22)
    during_gap = sum(gap_start <= area["reportingTime"] <= gap_end for area in physical22)
    after_gap = sum(area["reportingTime"] > gap_end for area in physical22)
    lines = [
        "",
        "## Actual 2022 reporting-time checkpoints",
        "",
        "Uses `TID_RD` from Valmyndigheten's reporting-time workbook. The noted reporting problem window is visible in the data.",
        f"Physical districts before 21:43: {before_gap:,}. During 21:43-22:16: {during_gap:,}. After 22:16: {after_gap:,}.",
        "",
        "| Time | Reported physical districts | Model areas available | Counted votes | Raw MAE | National MAE | Adjusted MAE | Local-neighbor MAE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for checkpoint in TIME_CHECKPOINTS:
        when = pd.Timestamp(checkpoint)
        counted, uncounted = areas_at_time(areas, when)
        physical_reported = sum(area["reportingTime"] <= when for area in physical22)
        counted_votes = total(counted, "22")["valid"]
        lines.append(
            f"| {when:%H:%M} | {physical_reported:,} | {len(counted):,} | {counted_votes:,.0f} | "
            f"{mae(raw_share(counted), target):.2f} | "
            f"{mae(national_forecast(counted, uncounted), target):.2f} | "
            f"{mae(adjusted_forecast(counted, uncounted), target):.2f} | "
            f"{mae(neighbor_forecast(counted, uncounted), target):.2f} |"
        )
    return lines


def write_report(districts: list[dict]) -> None:
    physical22 = load_physical_2022()
    inputs = model_inputs_for_order(districts, physical22)
    comparable = inputs["comparable"]
    municipality = [area for area in inputs["municipality"] if area["kind"] == "kommunrest"]
    county = [area for area in inputs["county"] if area["kind"] == "länsrest"]
    _, leftovers = municipality_remainders(comparable, physical22)
    fallback = county_fallback_remainders(leftovers, comparable, municipality)
    models = [
        ("A. Bara distriktsjämförbara områden", comparable),
        ("B. Distrikt + kommunrester", [*comparable, *municipality]),
        ("C. Distrikt + länsrester", [*comparable, *county]),
    ]
    target_total = total(comparable, "22")
    comparable_target = {party: share(target_total, party) for party in PARTIES}
    valnight_target = election_night_target()
    physical_votes = sum(area["valid22"] for area in physical22)
    lines = [
        "# Backtest 2022 replay prototype",
        "",
        "The val-night target is the preliminary 2022 Riksdag count from physical",
        "polling-station districts that have `TID_RD` reporting times from Valmyndigheten.",
        "Rows without municipality names or without `TID_RD` are excluded from the val-night target.",
        "",
        "Replay checkpoints use the official 2022 `TID_RD` order when the timing workbook is present.",
        "A synthetic remainder becomes counted only after all of its 2022 component districts",
        "have appeared in that reporting order.",
        "",
        "## Model coverage",
        "",
        "| Model | Areas in model | Remainder areas | 2022 votes represented | Share of val-night polling-station votes |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, areas in models:
        represented = sum(area["valid22"] for area in areas)
        remainder_count = sum(area["kind"] != "valdistrikt" for area in areas)
        lines.append(
            f"| {name} | {len(areas)} | {remainder_count} | {represented:,} | "
            f"{represented / physical_votes * 100:.2f}% |"
        )
    lines.extend([
        "",
        f"Kommunrester built: {len(municipality)}. Länsrester built for the coarse alternative: {len(county)}.",
        f"District components still left after kommunrester: {len(leftovers)}. A länsfallback after kommunrester would add {len(fallback)} areas in 2022.",
        "",
        "## Current model inside its own comparable set",
        "",
        "| Räknat jämförelseunderlag | Råläge MAE | Nationell jämförelseprognos MAE | Justerad prognos MAE |",
        "| --- | ---: | ---: | ---: |",
    ])
    for checkpoint in CHECKPOINTS:
        counted, uncounted = areas_at_checkpoint(comparable, checkpoint, len(physical22))
        lines.append(
            f"| {checkpoint}% | {mae(raw_share(counted), comparable_target):.2f} | "
            f"{mae(national_forecast(counted, uncounted), comparable_target):.2f} | "
            f"{mae(adjusted_forecast(counted, uncounted), comparable_target):.2f} |"
        )
    lines.extend([
        "",
        "## Three model inputs against whole val-night polling-station target",
        "",
        "The local-neighbor variant for model B borrows the observed swing from the narrowest available local bucket: same municipality first, then county + municipality type + historic profile, county + type, county + profile, county, and finally national fallback.",
        "",
        "| Simulated physical districts reported | A adjusted MAE | B adjusted MAE | C adjusted MAE | B local-neighbor MAE |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for checkpoint in CHECKPOINTS:
        counted_b, uncounted_b = areas_at_checkpoint(models[1][1], checkpoint, len(physical22))
        lines.append(
            f"| {checkpoint}% | "
            f"{model_error(models[0][1], checkpoint, len(physical22), valnight_target, adjusted_forecast):.2f} | "
            f"{model_error(models[1][1], checkpoint, len(physical22), valnight_target, adjusted_forecast):.2f} | "
            f"{model_error(models[2][1], checkpoint, len(physical22), valnight_target, adjusted_forecast):.2f} | "
            f"{mae(neighbor_forecast(counted_b, uncounted_b), valnight_target):.2f} |"
        )
    lines.extend([
        "",
        "## Whole val-night target benchmark for model A",
        "",
        "| Simulated physical districts reported | Råläge MAE | Nationell jämförelseprognos MAE | Justerad prognos MAE |",
        "| --- | ---: | ---: | ---: |",
    ])
    for checkpoint in CHECKPOINTS:
        counted, uncounted = areas_at_checkpoint(comparable, checkpoint, len(physical22))
        lines.append(
            f"| {checkpoint}% | {mae(raw_share(counted), valnight_target):.2f} | "
            f"{mae(national_forecast(counted, uncounted), valnight_target):.2f} | "
            f"{mae(adjusted_forecast(counted, uncounted), valnight_target):.2f} |"
        )
    lines.extend([
        "",
        "MAE is the mean absolute percentage-point error over the eight parties shown in the prototype.",
        "The real 2022 reporting order now comes from Valmyndigheten's `TID_RD` file.",
        "Wednesday collection-district votes and the final county-administration count",
        "are intentionally outside this val-night benchmark.",
    ])
    lines.extend(actual_time_summary(models[1][1], physical22, valnight_target))
    lines.extend(random_order_summary(districts, physical22, valnight_target))
    (ROOT / "backtest-2022.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote backtest-2022.md")


if __name__ == "__main__":
    replay = json.loads((ROOT / "data" / "riksdag-2022-replay.json").read_text(encoding="utf-8"))
    write_report([area for area in replay["districts"] if area["kind"] == "valdistrikt"])
