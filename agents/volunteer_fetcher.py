"""Fetch county-level volunteer data from Census CPS API."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import requests

from agents.base import DATA_RAW
from agents.state_utils import STATE_TO_FIPS, parse_state_filter

logger = logging.getLogger(__name__)

VOLUNTEER_RAW = DATA_RAW / "volunteer" / "cps_volunteer_county.csv"
CENSUS_CPS_URL = "https://api.census.gov/data/2021/cps/volunteer/sep"


def fetch_cps_volunteer_by_county(states: list[str] | None = None) -> pd.DataFrame:
    """
    Fetch volunteer rate by county from Census CPS API.

    Variable VOLORG2R = volunteered with an organization in past 12 months (%).
    """
    frames: list[pd.DataFrame] = []
    state_list = states if states else list(STATE_TO_FIPS.keys())

    for state in state_list:
        fips = STATE_TO_FIPS[state]
        params = {
            "get": "NAME,VOLORG2R",
            "for": "county:*",
            "in": f"state:{fips}",
        }
        try:
            resp = requests.get(CENSUS_CPS_URL, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            if len(data) < 2:
                continue
            df = pd.DataFrame(data[1:], columns=data[0])
            df["state_abbr"] = state
            df["county_fips"] = df["state"] + df["county"]
            df["volunteer_rate_pct"] = pd.to_numeric(df["VOLORG2R"], errors="coerce")
            df = df.rename(columns={"NAME": "county_name"})
            frames.append(df[["state_abbr", "county_fips", "county_name", "volunteer_rate_pct"]])
            logger.info("Fetched CPS volunteer data for %s: %d counties", state, len(df))
        except requests.RequestException as exc:
            logger.warning("CPS volunteer fetch failed for %s: %s", state, exc)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    VOLUNTEER_RAW.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(VOLUNTEER_RAW, index=False)
    return result


def ensure_volunteer_raw(states: list[str] | None, force_refresh: bool = False) -> Path | None:
    """Ensure volunteer CPS CSV exists; fetch if missing."""
    if VOLUNTEER_RAW.exists() and not force_refresh:
        return VOLUNTEER_RAW

    df = fetch_cps_volunteer_by_county(states)
    if df.empty:
        return None
    return VOLUNTEER_RAW
