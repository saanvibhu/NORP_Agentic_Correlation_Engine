"""Dataset-specific cleaning for IRS 990, Census ACS, CDC PLACES, and volunteer data."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from agents.dataset_registry import (
    CDC_MEASURES,
    IRS_COUNTY_METRICS,
    JOIN_KEY,
    STATE_KEY,
    DatasetSpec,
)
from agents.geo_utils import ensure_zip_county_map, extract_county_fips_from_geo_id, normalize_zip, zip_to_county_fips
from agents.state_utils import STATE_TO_NAME, parse_state_filter, county_fips_to_state

logger = logging.getLogger(__name__)

IRS_USECOLS = [
    "FILEREIN",
    "FILERNAME1",
    "TAXYEAR",
    "FILERUSSTATE",
    "FILERUSZIP",
    "FILERUSCITY",
    "TOTREVCURYEA",
    "TOTEXPCURYEA",
    "GOVERNGRANTS",
    "GRANTOORORGA",
    "TOTANBRVVOLU",
]

CENSUS_KEEP_COLS = {
    "GEO_ID": "geo_id",
    "NAME": "county_name",
    "DP03_0001E": "population_16_plus",
    "DP03_0009E": "unemployment_rate",
    "DP03_0062E": "median_household_income",
    "DP03_0088E": "per_capita_income",
    "DP03_0128E": "poverty_rate_all_people",
}


def _zero_fill_counties(
    county_df: pd.DataFrame,
    census_df: pd.DataFrame,
    states: list[str] | None,
) -> pd.DataFrame:
    """Left-join IRS aggregates onto full census county list; fill zeros for missing counties."""
    base = census_df[[STATE_KEY, JOIN_KEY, "county_name"]].drop_duplicates()
    if states:
        base = base[base[STATE_KEY].isin(states)]

    merged = base.merge(county_df, on=[STATE_KEY, JOIN_KEY], how="left", suffixes=("", "_dup"))
    for col in IRS_COUNTY_METRICS:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)
    return merged


def clean_irs_990(
    raw_path: Path,
    states: list[str] | None,
    census_df: pd.DataFrame,
    chunksize: int = 100_000,
    zip_county_map: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Filter IRS file by state(s), aggregate to county, zero-fill all census counties."""
    label = ",".join(states) if states else "ALL"
    logger.info("Processing IRS 990 (chunked, states=%s): %s", label, raw_path.name)

    if zip_county_map is None:
        zip_county_map = ensure_zip_county_map(census_df)

    chunks_out: list[pd.DataFrame] = []
    total_rows = 0

    for chunk in pd.read_csv(
        raw_path, usecols=IRS_USECOLS, chunksize=chunksize, low_memory=False
    ):
        total_rows += len(chunk)
        chunk["FILERUSSTATE"] = chunk["FILERUSSTATE"].astype(str).str.upper()
        if states:
            chunk = chunk[chunk["FILERUSSTATE"].isin(states)]
        if chunk.empty:
            continue
        chunks_out.append(chunk)

    if not chunks_out:
        empty = _zero_fill_counties(pd.DataFrame(), census_df, states)
        return empty, {"original_rows": total_rows, "final_rows": len(empty)}

    df = pd.concat(chunks_out, ignore_index=True)
    df["zip_code"] = df["FILERUSZIP"].apply(normalize_zip)
    df[STATE_KEY] = df["FILERUSSTATE"]
    df[JOIN_KEY] = df.apply(
        lambda r: zip_to_county_fips(r["zip_code"], mapping=zip_county_map, state=r[STATE_KEY]),
        axis=1,
    )

    for col in ("TOTREVCURYEA", "TOTEXPCURYEA", "GOVERNGRANTS", "GRANTOORORGA", "TOTANBRVVOLU"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("TAXYEAR", ascending=False).drop_duplicates(subset=["FILEREIN"], keep="first")
    mapped = df.dropna(subset=[JOIN_KEY])

    county = (
        mapped.groupby([STATE_KEY, JOIN_KEY], as_index=False)
        .agg(
            org_count=("FILEREIN", "nunique"),
            total_revenue=("TOTREVCURYEA", "sum"),
            total_expenses=("TOTEXPCURYEA", "sum"),
            total_gov_grants=("GOVERNGRANTS", "sum"),
            total_org_grants=("GRANTOORORGA", "sum"),
            total_volunteers=("TOTANBRVVOLU", "sum"),
            avg_revenue=("TOTREVCURYEA", "mean"),
            avg_expenses=("TOTEXPCURYEA", "mean"),
        )
    )
    county["volunteers_per_org"] = county["total_volunteers"] / county["org_count"].replace(0, pd.NA)

    county = _zero_fill_counties(county, census_df, states)

    report = {
        "original_rows": total_rows,
        "filtered_rows": len(df),
        "zip_mapped_rows": len(mapped),
        "counties_with_orgs": int((county["org_count"] > 0).sum()),
        "final_rows": len(county),
    }
    logger.info(
        "IRS %s: %d filings → %d counties (%d with orgs)",
        label,
        len(df),
        len(county),
        report["counties_with_orgs"],
    )
    return county, report


def clean_census_acs(
    raw_path: Path,
    states: list[str] | None,
) -> tuple[pd.DataFrame, dict]:
    """Extract county-level economic indicators, optionally filtered by state."""
    logger.info("Processing Census ACS DP03: %s", raw_path.name)

    df = pd.read_csv(raw_path, header=0, low_memory=False)
    df.columns = [c.strip().strip('"') for c in df.columns]

    available = [c for c in CENSUS_KEEP_COLS if c in df.columns]
    df = df[available].rename(columns={k: CENSUS_KEEP_COLS[k] for k in available})
    df[JOIN_KEY] = df["geo_id"].apply(extract_county_fips_from_geo_id)
    df[STATE_KEY] = df[JOIN_KEY].apply(county_fips_to_state)

    if states:
        df = df[df[STATE_KEY].isin(states)].copy()

    for col in df.columns:
        if col not in ("geo_id", "county_name", JOIN_KEY, STATE_KEY):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=[JOIN_KEY]).drop_duplicates(subset=[JOIN_KEY])
    return df, {"original_rows": len(df), "final_rows": len(df)}


def clean_cdc_places(
    raw_path: Path,
    states: list[str] | None,
) -> tuple[pd.DataFrame, dict]:
    """Pivot CDC PLACES county measures to wide format."""
    logger.info("Processing CDC PLACES: %s", raw_path.name)

    df = pd.read_csv(raw_path, low_memory=False)
    if states:
        df = df[df["StateAbbr"].isin(states)].copy()
    else:
        df = df.copy()

    df[JOIN_KEY] = df["LocationID"].astype(str).str.zfill(5)
    df[STATE_KEY] = df["StateAbbr"]
    df["Data_Value"] = pd.to_numeric(df["Data_Value"], errors="coerce")
    df = df[df["Data_Value_Type"].str.contains("Crude prevalence", case=False, na=False)]

    measures = [m for m in CDC_MEASURES if m in df["Measure"].unique()]
    subset = df[df["Measure"].isin(measures)]

    wide = subset.pivot_table(
        index=[STATE_KEY, JOIN_KEY, "LocationName"],
        columns="Measure",
        values="Data_Value",
        aggfunc="mean",
    ).reset_index()

    wide.columns = [
        str(c).lower().replace(" ", "_").replace(",", "").replace("-", "_")
        if c not in (STATE_KEY, JOIN_KEY, "LocationName")
        else c
        for c in wide.columns
    ]
    wide = wide.rename(columns={"LocationName": "county_name"})

    return wide, {"final_rows": len(wide), "measures_included": measures}


def clean_volunteer_cps(
    raw_path: Path,
    states: list[str] | None,
    irs_county_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Build county volunteer dataset from CPS rates + IRS volunteer counts.

    If CPS file missing, uses IRS volunteer metrics only.
    """
    logger.info("Processing volunteer county data")

    if irs_county_df is not None and not irs_county_df.empty:
        vol = irs_county_df[
            [STATE_KEY, JOIN_KEY, "county_name", "total_volunteers", "volunteers_per_org", "org_count"]
        ].copy()
    else:
        vol = pd.DataFrame()

    if raw_path.exists():
        cps = pd.read_csv(raw_path, dtype=str)
        cps["volunteer_rate_pct"] = pd.to_numeric(cps.get("volunteer_rate_pct"), errors="coerce")
        if states:
            cps = cps[cps[STATE_KEY].isin(states)]
        if not vol.empty:
            vol = vol.merge(
                cps[[STATE_KEY, JOIN_KEY, "volunteer_rate_pct"]],
                on=[STATE_KEY, JOIN_KEY],
                how="left",
            )
        else:
            vol = cps

    return vol, {"final_rows": len(vol)}


def clean_real_dataset(
    spec: DatasetSpec,
    raw_path: Path,
    states: list[str] | None = None,
    zip_county_map: dict[str, str] | None = None,
    census_df: pd.DataFrame | None = None,
    irs_county_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict]:
    if spec.name == "irs_990":
        if census_df is None:
            raise ValueError("census_df required for IRS cleaning")
        return clean_irs_990(raw_path, states, census_df, zip_county_map=zip_county_map)
    if spec.name == "census_acs_dp03":
        return clean_census_acs(raw_path, states)
    if spec.name == "cdc_places_county":
        return clean_cdc_places(raw_path, states)
    if spec.name == "volunteer_cps":
        return clean_volunteer_cps(raw_path, states, irs_county_df=irs_county_df)
    raise ValueError(f"No cleaner for dataset: {spec.name}")
