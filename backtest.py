from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
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


def raw_share(counted: list[dict]) -> dict[str, float]:
    counted_now = total(counted, "22")
    return {party: share(counted_now, party) for party in PARTIES}


def mae(estimate: dict[str, float], target: dict[str, float]) -> float:
    return sum(abs(estimate[party] - target[party]) for party in PARTIES) / len(PARTIES)


def election_night_target() -> dict[str, float]:
    source = pd.read_excel(ROOT / "preliminart-roster-per-distrikt-riksdagsvalet-2022.xlsx")
    physical = source[~source["Distrikt"].str.endswith("-0000")]
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
    source = pd.read_excel(ROOT / "preliminart-roster-per-distrikt-riksdagsvalet-2022.xlsx")
    source = source[~source["Distrikt"].str.endswith("-0000")].copy()
    source["code"] = source["Distrikt"].map(code_2022)
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
        })
    areas.sort(key=lambda area: (area["valid22"], area["id"]))
    for position, area in enumerate(areas, start=1):
        area["completeAt"] = position
    return areas


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
    }


def municipality_remainders(comparable: list[dict], physical22: list[dict]) -> tuple[list[dict], list[dict]]:
    all18 = load_physical_2018_by_municipality()
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


def attach_complete_positions(districts: list[dict], physical22: list[dict]) -> list[dict]:
    positions = {int(area["id"]): area["completeAt"] for area in physical22}
    positioned = []
    for district in districts:
        current = dict(district)
        current["completeAt"] = positions[int(current["id"])]
        current["kind"] = "valdistrikt"
        positioned.append(current)
    return positioned


def model_error(areas: list[dict], checkpoint: int, physical_count: int, target: dict, method) -> float:
    counted, uncounted = areas_at_checkpoint(areas, checkpoint, physical_count)
    return mae(method(counted, uncounted), target)


def write_report(districts: list[dict]) -> None:
    physical22 = load_physical_2022()
    comparable = attach_complete_positions(districts, physical22)
    municipality, leftovers = municipality_remainders(comparable, physical22)
    county = county_remainders(comparable, physical22)
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
        "polling-station districts in Valmyndigheten's preliminary district file.",
        "Collection-district rows ending in `-0000` are excluded.",
        "",
        "All replay checkpoints still use a size-based order of 2022 physical",
        "districts. A synthetic remainder becomes counted only after all of its",
        "2022 component districts have appeared in that simulated order.",
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
        "| Simulated physical districts reported | A adjusted MAE | B adjusted MAE | C adjusted MAE |",
        "| --- | ---: | ---: | ---: |",
    ])
    for checkpoint in CHECKPOINTS:
        lines.append(
            f"| {checkpoint}% | "
            f"{model_error(models[0][1], checkpoint, len(physical22), valnight_target, adjusted_forecast):.2f} | "
            f"{model_error(models[1][1], checkpoint, len(physical22), valnight_target, adjusted_forecast):.2f} | "
            f"{model_error(models[2][1], checkpoint, len(physical22), valnight_target, adjusted_forecast):.2f} |"
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
        "The real 2022 reporting order is still the missing verification input.",
        "Wednesday collection-district votes and the final county-administration count",
        "are intentionally outside this val-night benchmark.",
    ])
    (ROOT / "backtest-2022.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote backtest-2022.md")


if __name__ == "__main__":
    replay = json.loads((ROOT / "data" / "riksdag-2022-replay.json").read_text(encoding="utf-8"))
    write_report([area for area in replay["districts"] if area["kind"] == "valdistrikt"])
