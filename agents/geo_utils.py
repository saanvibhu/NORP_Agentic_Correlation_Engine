"""Geographic utilities for joining datasets at county level."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from io import StringIO

import pandas as pd
import requests
import zipcodes

from agents.base import PROJECT_ROOT

logger = logging.getLogger(__name__)

REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
ZIP_COUNTY_CACHE = REFERENCE_DIR / "zip_county_map.csv"
HUD_ZIP_COUNTY_URL = (
    "https://www.huduser.gov/portal/datasets/usps/ZIP_COUNTY_122024.csv"
)


def extract_county_fips_from_geo_id(geo_id: str) -> str | None:
    """Convert Census GEO_ID (0500000US13001) to 5-digit county FIPS (13001)."""
    if pd.isna(geo_id):
        return None
    text = str(geo_id).strip().strip('"')
    if "US" in text:
        return text.split("US")[-1].zfill(5)
    return text.zfill(5)


def normalize_zip(value) -> str | None:
    if pd.isna(value):
        return None
    digits = "".join(c for c in str(value) if c.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return None


def _normalize_county_name(name: str) -> str:
    text = str(name).lower()
    text = text.split(",")[0]
    text = re.sub(r"\bcounty\b", "", text)
    text = re.sub(r"[^a-z ]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def build_zip_county_map_from_census(
    census_county_names: list[str],
    county_fips: list[str],
    state_abbrs: list[str] | None = None,
) -> dict[str, str]:
    """Map zip codes to county FIPS using zipcodes + Census county names."""
    if state_abbrs is None:
        state_abbrs = ["GA"] * len(county_fips)

    name_to_fips: dict[tuple[str, str], str] = {}
    for name, fips, st in zip(census_county_names, county_fips, state_abbrs):
        name_to_fips[(_normalize_county_name(name), st)] = str(fips).zfill(5)

    target_states = set(state_abbrs)
    mapping: dict[str, str] = {}
    for entry in zipcodes.list_all():
        st = entry.get("state")
        if st not in target_states:
            continue
        zip_code = entry["zip_code"]
        county_key = _normalize_county_name(entry.get("county", ""))
        fips = name_to_fips.get((county_key, st))
        if not fips:
            for (census_name, census_st), census_fips in name_to_fips.items():
                if census_st == st and (county_key in census_name or census_name in county_key):
                    fips = census_fips
                    break
        if fips:
            mapping[zip_code] = fips

    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"zip_code": k, "county_fips": v} for k, v in sorted(mapping.items())]
    ).to_csv(ZIP_COUNTY_CACHE, index=False)
    logger.info("Built zip→county map: %d zips (%s)", len(mapping), ",".join(sorted(target_states)))
    return mapping


def _build_zip_county_from_hud() -> dict[str, str]:
    """Download HUD ZIP→County crosswalk and filter to Georgia (state FIPS 13)."""
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading HUD ZIP-County crosswalk...")
    response = requests.get(HUD_ZIP_COUNTY_URL, timeout=60)
    response.raise_for_status()

    hud = pd.read_csv(StringIO(response.text), dtype=str)
    hud.columns = [c.strip().upper() for c in hud.columns]

    zip_col = next(c for c in hud.columns if c == "ZIP")
    county_col = next(c for c in hud.columns if c == "COUNTY")

    hud["zip_code"] = hud[zip_col].str.zfill(5)
    hud["county_fips"] = hud[county_col].str.zfill(5)
    ga = hud[hud["county_fips"].str.startswith("13")].copy()

    if "RES_RATIO" in hud.columns:
        ga["RES_RATIO"] = pd.to_numeric(ga["RES_RATIO"], errors="coerce").fillna(0)
        ga = ga.sort_values("RES_RATIO", ascending=False).drop_duplicates("zip_code")

    mapping = dict(zip(ga["zip_code"], ga["county_fips"]))
    pd.DataFrame(
        [{"zip_code": k, "county_fips": v} for k, v in mapping.items()]
    ).to_csv(ZIP_COUNTY_CACHE, index=False)
    logger.info("Cached %d GA zip→county mappings from HUD", len(mapping))
    return mapping


@lru_cache(maxsize=1)
def _load_zip_county_map() -> dict[str, str]:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    if ZIP_COUNTY_CACHE.exists():
        df = pd.read_csv(ZIP_COUNTY_CACHE, dtype=str)
        if len(df) > 0:
            return dict(zip(df["zip_code"], df["county_fips"]))

    return {}


def ensure_zip_county_map(census_df: pd.DataFrame) -> dict[str, str]:
    """Build or load zip→county map using Census county names."""
    cached = _load_zip_county_map()
    if cached:
        return cached

    if "county_name" in census_df.columns and "county_fips" in census_df.columns:
        states = census_df["state_abbr"].tolist() if "state_abbr" in census_df.columns else None
        return build_zip_county_map_from_census(
            census_df["county_name"].tolist(),
            census_df["county_fips"].astype(str).tolist(),
            state_abbrs=states,
        )

    try:
        return _build_zip_county_from_hud()
    except Exception as exc:
        logger.warning("Could not build zip→county map: %s", exc)
        return {}


def zip_to_county_fips(
    zip_code: str | None,
    mapping: dict[str, str] | None = None,
    state: str = "GA",
) -> str | None:
    if not zip_code:
        return None
    z = normalize_zip(zip_code)
    if not z:
        return None

    mapping = mapping or _load_zip_county_map()
    if z in mapping:
        return mapping[z]

    if state == "GA" and z[:2] in ("30", "31", "39"):
        return None
    return None
