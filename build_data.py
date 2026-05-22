from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
PARTIES = {
    "Moderaterna": "M",
    "Centerpartiet": "C",
    "Liberalerna": "L",
    "Kristdemokraterna": "KD",
    "Socialdemokraterna": "S",
    "Vänsterpartiet": "V",
    "Miljöpartiet": "MP",
    "Sverigedemokraterna": "SD",
}
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


def id_from_2022(raw_id: str) -> int:
    return int(raw_id.replace("RD-", "").replace("-", ""))


def number(value) -> int:
    if pd.isna(value):
        return 0
    return int(value)


def load_2022() -> dict[int, dict]:
    source = pd.read_excel(ROOT / "preliminart-roster-per-distrikt-riksdagsvalet-2022.xlsx")
    source["code"] = source["Distrikt"].map(id_from_2022)
    physical = source[source["code"].astype(str).str[-4:] != "0000"]
    districts = {}

    for code, rows in physical.groupby("code", sort=False):
        first = rows.iloc[0]
        vote_rows = rows.set_index("Parti")
        valid = number(vote_rows.loc["Summa giltiga röster", "Röster"])
        turnout = vote_rows.loc["Valdeltagande"]
        districts[code] = {
            "id": str(code),
            "kind": "valdistrikt",
            "name": str(first["Distrikt"]),
            "municipality": str(first["Kommun"]),
            "county": str(first["Län"]),
            "constituency": str(first["Valkrets"]),
            "electorate": number(turnout["Röstberättigade"]),
            "valid22": valid,
            "votes22": {
                short: number(vote_rows.loc[full_name, "Röster"])
                for full_name, short in PARTIES.items()
            },
        }
    return districts


def add_physical_replay_positions(districts: dict[int, dict]) -> None:
    ordered = sorted(districts.values(), key=lambda district: (district["valid22"], district["id"]))
    for position, district in enumerate(ordered):
        district["physicalReplayOrder"] = position


def load_2018() -> pd.DataFrame:
    base = pd.read_excel(ROOT / "2018_R_per_valdistrikt.xlsx", sheet_name="R antal")
    base["code"] = (
        base["LÄNSKOD"].map(lambda value: f"{number(value):02}")
        + base["KOMMUNKOD"].map(lambda value: f"{number(value):02}")
        + base["VALDISTRIKTSKOD"].map(lambda value: f"{number(value):04}")
    ).astype(int)
    columns = ["code", "RÖSTER GILTIGA", *PARTY_META.keys()]
    base = base[columns].fillna(0)
    return base.groupby("code", as_index=True).sum(numeric_only=True)


def load_2018_municipalities() -> dict[str, dict]:
    base = pd.read_excel(ROOT / "2018_R_per_valdistrikt.xlsx", sheet_name="R antal").fillna(0)
    physical = base[base["VALDISTRIKTSKOD"].ne(0)].copy()
    physical["municipalityCode"] = (
        physical["LÄNSKOD"].map(lambda value: f"{number(value):02d}")
        + physical["KOMMUNKOD"].map(lambda value: f"{number(value):02d}")
    )
    grouped = {}
    for code, rows in physical.groupby("municipalityCode"):
        grouped[code] = {
            "valid": number(rows["RÖSTER GILTIGA"].sum()),
            "votes": {party: number(rows[party].sum()) for party in PARTY_META},
        }
    return grouped


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


def historic_profile(district: dict) -> str:
    shares = {
        party: district["votes18"][party] / district["valid18"] * 100
        for party in PARTY_META
    }
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


def append_comparable_baselines(districts: dict[int, dict]) -> list[dict]:
    baseline = load_2018()
    municipality_groups = load_municipality_groups()
    mapping = pd.read_excel(
        ROOT / "jamforelser-2018-2022.xlsx",
        sheet_name="Fysiska valdistrikt",
    )
    mapped = []

    for _, row in mapping.iterrows():
        code22 = number(row["Kod_2022"])
        current = districts.get(code22)
        if not current or str(row["Jämförbart"]).lower() == "nej":
            continue
        current["name"] = str(row["Valdistrikt"])
        current["municipalityCode"] = f"{code22 // 10000:04d}"
        current.update(
            municipality_groups.get(
                current["municipalityCode"],
                {
                    "municipalityGroupCode": "NA",
                    "municipalityBand": "Okänd kommuntyp",
                    "municipalityType": "Okänd kommuntyp",
                },
            )
        )

        predecessor_codes = [
            number(row[column])
            for column in ["Valdistriktskod2018", "Kod 2 2018", "Kod 3 2018"]
            if number(row[column])
        ]
        if not predecessor_codes and str(row["Jämförbart"]).lower() == "ja":
            predecessor_codes = [code22]
        matched = baseline.reindex(predecessor_codes).dropna(how="all")
        if matched.empty:
            continue

        current["valid18"] = number(matched["RÖSTER GILTIGA"].sum())
        current["votes18"] = {
            party: number(matched[party].sum())
            for party in PARTY_META
        }
        if current["valid18"] and current["valid22"]:
            current["historicProfile"] = historic_profile(current)
            mapped.append(current)

    return mapped


def sum_areas(areas: list[dict], valid_key: str, vote_key: str) -> dict:
    return {
        "valid": sum(area[valid_key] for area in areas),
        "votes": {
            party: sum(area[vote_key][party] for area in areas)
            for party in PARTY_META
        },
    }


def municipality_remainders(physical: dict[int, dict], comparable: list[dict]) -> list[dict]:
    municipal18 = load_2018_municipalities()
    municipal_groups = load_municipality_groups()
    comparable_ids = {int(area["id"]) for area in comparable}
    components = {}
    for district in physical.values():
        if int(district["id"]) in comparable_ids:
            continue
        code = f"{int(district['id']) // 10000:04d}"
        components.setdefault(code, []).append(district)

    comparable_by_municipality = {}
    for area in comparable:
        comparable_by_municipality.setdefault(area["municipalityCode"], []).append(area)

    remainders = []
    for code, current_components in components.items():
        if code not in municipal18:
            continue
        comparable_base = sum_areas(comparable_by_municipality.get(code, []), "valid18", "votes18")
        valid18 = municipal18[code]["valid"] - comparable_base["valid"]
        votes18 = {
            party: municipal18[code]["votes"][party] - comparable_base["votes"][party]
            for party in PARTY_META
        }
        if valid18 <= 0 or any(votes < 0 for votes in votes18.values()):
            continue
        current = sum_areas(current_components, "valid22", "votes22")
        meta = current_components[0]
        remainder = {
            "id": f"kommunrest-{code}",
            "kind": "kommunrest",
            "name": f"{meta['municipality']} kommunrest",
            "municipality": meta["municipality"],
            "municipalityCode": code,
            "county": meta["county"],
            "constituency": meta["constituency"],
            "electorate": 0,
            "valid18": valid18,
            "votes18": votes18,
            "valid22": current["valid"],
            "votes22": current["votes"],
            "componentDistricts": len(current_components),
            "physicalReplayOrder": max(area["physicalReplayOrder"] for area in current_components),
        }
        remainder.update(
            municipal_groups.get(
                code,
                {
                    "municipalityGroupCode": "NA",
                    "municipalityBand": "Okänd kommuntyp",
                    "municipalityType": "Okänd kommuntyp",
                },
            )
        )
        remainder["historicProfile"] = historic_profile(remainder)
        remainders.append(remainder)
    return remainders


def add_replay_order(districts: list[dict]) -> None:
    # Early Swedish val-night reporting is heavily shaped by district size.
    districts.sort(key=lambda district: (district["physicalReplayOrder"], district["kind"], district["id"]))
    for position, district in enumerate(districts):
        district["replayOrder"] = position


def write_dataset(districts: list[dict]) -> None:
    payload = {
        "source": "Valmyndigheten preliminary district count for the 2022 Riksdag election, 2018 district results, and 2018-2022 district comparison file.",
        "method": "Comparable physical districts plus synthetic municipality remainder areas. A remainder appears after all its 2022 physical component districts have appeared in the size-first replay. Municipality groups use SKR 2023.",
        "parties": PARTY_META,
        "districts": districts,
    }
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "riksdag-2022-replay.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (data_dir / "riksdag-2022-replay.js").write_text(
        "window.RIKSDAG_REPLAY_DATA="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";",
        encoding="utf-8",
    )
    comparable = sum(district["kind"] == "valdistrikt" for district in districts)
    remainders = sum(district["kind"] == "kommunrest" for district in districts)
    print(f"Wrote {comparable} comparable districts and {remainders} municipality remainders.")


if __name__ == "__main__":
    physical = load_2022()
    add_physical_replay_positions(physical)
    comparable = append_comparable_baselines(physical)
    remainders = municipality_remainders(physical, comparable)
    model_areas = [*comparable, *remainders]
    add_replay_order(model_areas)
    write_dataset(model_areas)
