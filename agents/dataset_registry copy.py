"""Registry of real and sample datasets used by the agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agents.base import DATA_RAW
from agents.state_utils import parse_state_filter

DEFAULT_STATE_FILTER = "GA"


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    source: str
    raw_path: str
    processed_name: str
    description: str
    is_large: bool = False
    requires_state_filter: bool = False


REAL_DATASETS: list[DatasetSpec] = [
    DatasetSpec(
        name="irs_990",
        source="IRS Form 990 Standard Fields",
        raw_path="irs/2025_10_18_All_Years_990StandardFields.csv",
        processed_name="irs_990_county.csv",
        description="Nonprofit tax filings aggregated to county: revenue, expenses, grants, volunteers",
        is_large=True,
        requires_state_filter=True,
    ),
    DatasetSpec(
        name="census_acs_dp03",
        source="U.S. Census Bureau ACS DP03",
        raw_path="census/ACSDP5Y2023.DP03-Data.csv",
        processed_name="census_acs_dp03_county.csv",
        description="County economic characteristics: income, unemployment, poverty",
        requires_state_filter=True,
    ),
    DatasetSpec(
        name="cdc_places_county",
        source="CDC PLACES County Data 2025",
        raw_path="cdc/CDCPLACES_county_2025.csv",
        processed_name="cdc_places_county.csv",
        description="County health outcomes and behaviors from CDC PLACES",
        requires_state_filter=True,
    ),
    DatasetSpec(
        name="volunteer_cps",
        source="U.S. Census CPS Volunteer Supplement",
        raw_path="volunteer/cps_volunteer_county.csv",
        processed_name="volunteer_county.csv",
        description="County volunteer participation rates from Census CPS (optional fetch)",
        requires_state_filter=True,
    ),
]

SAMPLE_DATASETS: list[DatasetSpec] = [
    DatasetSpec(
        name="sample_nonprofit_funding",
        source="NORP Metabase (sample)",
        raw_path="sample_nonprofit_funding.csv",
        processed_name="sample_nonprofit_funding.csv",
        description="Sample nonprofit funding and volunteer metrics",
    ),
    DatasetSpec(
        name="sample_demographics",
        source="Census Bureau (sample)",
        raw_path="sample_demographics.csv",
        processed_name="sample_demographics.csv",
        description="Sample zip-level demographics",
    ),
    DatasetSpec(
        name="sample_volunteer_engagement",
        source="Data.gov (sample)",
        raw_path="sample_volunteer_engagement.csv",
        processed_name="sample_volunteer_engagement.csv",
        description="Sample volunteer hours and retention by zip",
    ),
]

JOIN_KEY = "county_fips"
STATE_KEY = "state_abbr"

CDC_MEASURES = [
    "Obesity among adults",
    "Depression among adults",
    "Fair or poor self-rated health status among adults",
    "Food insecurity in the past 12 months among adults",
    "Housing insecurity in the past 12 months among adults",
    "Binge drinking among adults",
    "Current lack of health insurance among adults",
    "Any disability among adults",
]

IRS_COUNTY_METRICS = [
    "org_count",
    "total_revenue",
    "total_expenses",
    "total_gov_grants",
    "total_org_grants",
    "total_volunteers",
    "avg_revenue",
    "avg_expenses",
    "volunteers_per_org",
]


def resolve_raw_path(spec: DatasetSpec, raw_dir: Path | None = None) -> Path:
    return (raw_dir or DATA_RAW) / spec.raw_path


def get_catalog(use_real: bool = True) -> list[DatasetSpec]:
    return REAL_DATASETS if use_real else SAMPLE_DATASETS


def active_real_specs(states: list[str] | None = None) -> list[DatasetSpec]:
    """Return all real dataset specs (volunteer always included — uses IRS if CPS missing)."""
    return list(REAL_DATASETS)
