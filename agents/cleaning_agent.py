"""Agent 2: Data Cleaning — standardizes and normalizes datasets."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from agents.base import DATA_PROCESSED, DATA_RAW, AgentResult, save_json, setup_logger
from agents.dataset_registry import (
    DEFAULT_STATE_FILTER,
    SAMPLE_DATASETS,
    DatasetSpec,
    get_catalog,
    resolve_raw_path,
)
from agents.geo_utils import ensure_zip_county_map
from agents.real_data_cleaners import clean_real_dataset
from agents.state_utils import parse_state_filter
from agents.volunteer_fetcher import ensure_volunteer_raw

logger = setup_logger(__name__)

# US state abbreviations for location normalization
STATE_MAP = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}

DATE_COLUMNS = {"date", "founded_date", "report_date", "year"}
LOCATION_COLUMNS = {"city", "state", "location", "city_state"}
NAME_COLUMNS = {"nonprofit_name", "organization_name", "org_name", "name"}


class CleaningAgent:
    """Detects nulls, removes duplicates, and standardizes fields."""

    def __init__(
        self,
        raw_dir: Path | None = None,
        processed_dir: Path | None = None,
        use_real_data: bool = True,
        state_filter: str = DEFAULT_STATE_FILTER,
    ):
        self.raw_dir = raw_dir or DATA_RAW
        self.processed_dir = processed_dir or DATA_PROCESSED
        self.use_real_data = use_real_data
        self.state_filter = state_filter
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_org_name(value: str) -> str:
        if pd.isna(value):
            return value
        name = str(value).strip().upper()
        name = re.sub(r"\s+", " ", name)
        name = re.sub(r"[^\w\s&'-]", "", name)
        for suffix in (" INC", " LLC", " CORP", " FOUNDATION"):
            if name.endswith(suffix):
                name = name[: -len(suffix)].strip()
        return name.title()

    @staticmethod
    def normalize_location(value: str) -> str:
        if pd.isna(value):
            return value
        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)

        # "Atlanta, GA" or "Atlanta, Georgia"
        if "," in text:
            parts = [p.strip() for p in text.split(",") if p.strip()]
            if len(parts) >= 2:
                city = parts[0].title()
                state_part = parts[-1].lower()
                if state_part in STATE_MAP:
                    return f"{city}, {STATE_MAP[state_part]}"
                if len(state_part) == 2:
                    return f"{city}, {state_part.upper()}"

        # "Atlanta Georgia" or "Atlanta GA"
        tokens = text.split()
        if len(tokens) >= 2:
            state_part = tokens[-1].lower()
            city = " ".join(tokens[:-1]).title()
            if state_part in STATE_MAP:
                return f"{city}, {STATE_MAP[state_part]}"
            if len(state_part) == 2:
                return f"{city}, {state_part.upper()}"

        return text.title()

    @staticmethod
    def normalize_state(value: str) -> str:
        if pd.isna(value):
            return value
        text = str(value).strip().lower()
        if text in STATE_MAP:
            return STATE_MAP[text]
        if len(text) == 2:
            return text.upper()
        return str(value).strip().upper()

    def standardize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            if col.lower() in DATE_COLUMNS or "date" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif col.lower() == "year":
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        return df

    def standardize_locations(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            lower = col.lower()
            if lower in LOCATION_COLUMNS:
                df[col] = df[col].apply(self.normalize_location)
            elif lower == "state":
                df[col] = df[col].apply(self.normalize_state)
        return df

    def normalize_names(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            if col.lower() in NAME_COLUMNS:
                df[col] = df[col].apply(self.normalize_org_name)
        return df

    def handle_nulls(self, df: pd.DataFrame, drop_threshold: float = 0.5) -> pd.DataFrame:
        """Drop columns with >50% nulls; leave remaining nulls for validation agent."""
        null_pct = df.isnull().mean()
        drop_cols = null_pct[null_pct > drop_threshold].index.tolist()
        if drop_cols:
            logger.info("Dropping high-null columns: %s", drop_cols)
            df = df.drop(columns=drop_cols)
        return df

    def clean(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        original_rows = len(df)
        report: dict = {
            "original_rows": original_rows,
            "duplicates_removed": 0,
            "null_columns_dropped": [],
        }

        df = self.handle_nulls(df)
        df = self.standardize_dates(df)
        df = self.standardize_locations(df)
        df = self.normalize_names(df)

        before_dedup = len(df)
        df = df.drop_duplicates()
        report["duplicates_removed"] = before_dedup - len(df)
        report["final_rows"] = len(df)
        report["row_loss_pct"] = round(
            (original_rows - len(df)) / max(original_rows, 1) * 100, 2
        )
        return df, report

    def clean_spec(self, spec: DatasetSpec) -> AgentResult:
        """Clean a single dataset spec (used for sample mode)."""
        return self._clean_one(spec)

    def _clean_one(
        self,
        spec: DatasetSpec,
        states: list[str] | None = None,
        census_df: pd.DataFrame | None = None,
        zip_map: dict[str, str] | None = None,
        irs_df: pd.DataFrame | None = None,
    ) -> AgentResult:
        raw_path = resolve_raw_path(spec, self.raw_dir)
        if not raw_path.exists() and spec.name != "volunteer_cps":
            return AgentResult(
                agent="cleaning",
                success=False,
                message=f"File not found: {raw_path}",
            )

        if self.use_real_data:
            if states is None:
                states = parse_state_filter(self.state_filter)
            if spec.name == "volunteer_cps":
                ensure_volunteer_raw(states)
            cleaned, report = clean_real_dataset(
                spec,
                raw_path,
                states=states,
                zip_county_map=zip_map,
                census_df=census_df,
                irs_county_df=irs_df,
            )
        else:
            cleaned, report = self.clean(pd.read_csv(raw_path))

        if cleaned.empty:
            return AgentResult(
                agent="cleaning",
                success=False,
                message=f"No rows after cleaning {spec.name}",
                data={"report": report},
            )

        dest = self.processed_dir / spec.processed_name
        cleaned.to_csv(dest, index=False)
        logger.info("Cleaned %s → %s (%d rows)", spec.name, spec.processed_name, len(cleaned))
        return AgentResult(
            agent="cleaning",
            success=True,
            message=f"Cleaned {spec.name}",
            data={"path": str(dest), "report": report, "dataframe": cleaned},
        )

    def clean_file(self, filename: str) -> AgentResult:
        src = self.raw_dir / filename
        if not src.exists():
            return AgentResult(
                agent="cleaning",
                success=False,
                message=f"File not found: {src}",
            )

        df = pd.read_csv(src)
        cleaned, report = self.clean(df)
        dest = self.processed_dir / filename
        cleaned.to_csv(dest, index=False)
        logger.info("Cleaned %s: %d → %d rows", filename, report["original_rows"], report["final_rows"])

        return AgentResult(
            agent="cleaning",
            success=True,
            message=f"Cleaned {filename}",
            data={"path": str(dest), "report": report},
        )

    def run(
        self,
        filenames: list[str] | None = None,
        specs: list[DatasetSpec] | None = None,
    ) -> AgentResult:
        if specs is not None:
            states = parse_state_filter(self.state_filter)
            order = {"census_acs_dp03": 0, "irs_990": 1, "cdc_places_county": 2, "volunteer_cps": 3}
            ordered = sorted(specs, key=lambda s: order.get(s.name, 9))

            census_df = None
            zip_map = None
            irs_df = None
            results = []

            for spec in ordered:
                if spec.name == "volunteer_cps" and not resolve_raw_path(spec, self.raw_dir).exists():
                    vol_result = self._clean_one(spec, states=states, irs_df=irs_df)
                    results.append(vol_result)
                    continue

                r = self._clean_one(
                    spec,
                    states=states,
                    census_df=census_df,
                    zip_map=zip_map,
                    irs_df=irs_df,
                )
                if r.success and r.data:
                    df = r.data.get("dataframe")
                    if spec.name == "census_acs_dp03" and df is not None:
                        census_df = df
                        zip_map = ensure_zip_county_map(census_df)
                    elif spec.name == "irs_990" and df is not None:
                        irs_df = df
                # Remove dataframe from serializable output
                if r.data and "dataframe" in r.data:
                    del r.data["dataframe"]
                results.append(r)
        elif self.use_real_data:
            results = [self.clean_spec(spec) for spec in get_catalog(use_real=True)]
        else:
            if filenames is None:
                filenames = [
                    p.name for p in sorted(self.raw_dir.glob("sample_*.csv"))
                ]
            results = [self.clean_file(name) for name in filenames]

        summary = {
            "files_processed": len(results),
            "successful": sum(1 for r in results if r.success),
            "details": [r.to_dict() for r in results],
        }
        save_json(summary, self.processed_dir / "cleaning_report.json")

        return AgentResult(
            agent="cleaning",
            success=summary["successful"] > 0,
            message=f"Cleaned {summary['successful']}/{summary['files_processed']} files",
            data=summary,
        )


if __name__ == "__main__":
    result = CleaningAgent().run()
    print(result.message)
