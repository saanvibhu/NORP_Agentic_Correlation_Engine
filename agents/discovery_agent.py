"""Agent 1: Dataset Discovery — finds, imports, and scores datasets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from agents.base import DATA_RAW, AgentResult, load_csv, save_json, setup_logger
from agents.dataset_registry import SAMPLE_DATASETS, REAL_DATASETS, DatasetSpec, resolve_raw_path

logger = setup_logger(__name__)

# Keywords that signal relevance to nonprofit sociological research
RELEVANCE_KEYWORDS = {
    "nonprofit": 15,
    "organization": 10,
    "volunteer": 15,
    "donation": 12,
    "funding": 12,
    "revenue": 10,
    "grant": 10,
    "impact": 8,
    "community": 8,
    "education": 8,
    "income": 8,
    "unemployment": 8,
    "population": 6,
    "state": 4,
    "city": 4,
    "zip": 4,
    "county": 4,
    "retention": 10,
    "engagement": 8,
    "irs": 6,
    "501": 6,
    "census": 6,
    "demographic": 6,
}

# Legacy catalog entries (sample datasets at data/raw root)
DATASET_CATALOG = [
    {
        "name": spec.name,
        "source": spec.source,
        "path": spec.raw_path,
        "description": spec.description,
    }
    for spec in SAMPLE_DATASETS
]


@dataclass
class DatasetRecord:
    """Metadata for a discovered dataset."""

    name: str
    source: str
    path: str
    description: str
    relevance_score: float = 0.0
    row_count: int = 0
    column_count: int = 0
    schema: dict[str, str] = field(default_factory=dict)
    status: str = "discovered"


class DiscoveryAgent:
    """Discovers datasets, examines schemas, and assigns relevance scores."""

    def __init__(
        self,
        raw_dir: Path | None = None,
        min_relevance: float = 30.0,
        use_real_data: bool = True,
    ):
        self.raw_dir = raw_dir or DATA_RAW
        self.min_relevance = min_relevance
        self.use_real_data = use_real_data
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _catalog_specs(self) -> list[DatasetSpec]:
        return REAL_DATASETS if self.use_real_data else SAMPLE_DATASETS

    def _peek_dataframe(self, path: Path, spec: DatasetSpec) -> pd.DataFrame:
        """Load schema sample without reading huge files fully."""
        if spec.is_large:
            if spec.name == "irs_990":
                return pd.read_csv(path, nrows=5000, low_memory=False)
            return pd.read_csv(path, nrows=1000, low_memory=False)
        if spec.name == "census_acs_dp03":
            return pd.read_csv(path, nrows=50, low_memory=False)
        return load_csv(path)

    def _estimate_row_count(self, path: Path, spec: DatasetSpec, sample: pd.DataFrame) -> int:
        if not spec.is_large:
            return len(load_csv(path)) if spec.name != "census_acs_dp03" else len(sample) - 1
        # Fast line count for large CSV (minus header)
        with path.open("rb") as f:
            lines = sum(1 for _ in f) - 1
        return max(lines, 0)

    def discover_spec(self, spec: DatasetSpec) -> DatasetRecord | None:
        path = resolve_raw_path(spec, self.raw_dir)
        if not path.exists():
            if spec.name == "volunteer_cps":
                # Optional — IRS provides volunteer metrics if CPS file absent
                return DatasetRecord(
                    name=spec.name,
                    source=spec.source,
                    path=str(path),
                    description=spec.description + " (will use IRS volunteer fields)",
                    relevance_score=50.0,
                    row_count=0,
                    column_count=0,
                    status="optional",
                )
            logger.warning("File not found: %s", path)
            return None

        sample = self._peek_dataframe(path, spec)
        relevance = self.score_relevance(sample.columns, spec.description)
        row_count = self._estimate_row_count(path, spec, sample)

        record = DatasetRecord(
            name=spec.name,
            source=spec.source,
            path=str(path),
            description=spec.description,
            relevance_score=relevance,
            row_count=row_count,
            column_count=len(sample.columns),
            schema={col: str(dtype) for col, dtype in sample.dtypes.items()},
            status="imported" if relevance >= self.min_relevance else "low_relevance",
        )
        logger.info(
            "Discovered %s — relevance=%.1f, rows=%d",
            record.name,
            record.relevance_score,
            record.row_count,
        )
        return record

    def score_relevance(self, columns: Iterable[str], description: str = "") -> float:
        """Score dataset relevance based on column names and description."""
        text = " ".join(columns).lower() + " " + description.lower()
        score = 0.0
        for keyword, weight in RELEVANCE_KEYWORDS.items():
            if keyword in text:
                score += weight
        # Description carries strong signal for wide tables (Census, CDC)
        desc_words = [w for w in re.split(r"\W+", description.lower()) if len(w) > 3]
        score += min(len(desc_words) * 3, 30)
        return min(score, 100.0)

    def examine_schema(self, df: pd.DataFrame) -> dict[str, str]:
        return {col: str(dtype) for col, dtype in df.dtypes.items()}

    def discover_local(self, filename: str) -> DatasetRecord | None:
        path = self.raw_dir / filename
        if not path.exists():
            logger.warning("File not found: %s", path)
            return None

        df = load_csv(path)
        catalog_entry = next(
            (d for d in DATASET_CATALOG if d["path"] == filename), {}
        )
        relevance = self.score_relevance(
            df.columns, catalog_entry.get("description", "")
        )

        record = DatasetRecord(
            name=catalog_entry.get("name", path.stem),
            source=catalog_entry.get("source", "local"),
            path=str(path),
            description=catalog_entry.get("description", ""),
            relevance_score=relevance,
            row_count=len(df),
            column_count=len(df.columns),
            schema=self.examine_schema(df),
            status="imported" if relevance >= self.min_relevance else "low_relevance",
        )
        logger.info(
            "Discovered %s — relevance=%.1f, rows=%d",
            record.name,
            record.relevance_score,
            record.row_count,
        )
        return record

    def discover_catalog(self) -> list[DatasetRecord]:
        """Discover datasets from the active catalog (real or sample)."""
        records: list[DatasetRecord] = []
        for spec in self._catalog_specs():
            record = self.discover_spec(spec)
            if record:
                records.append(record)
        return records

    def get_accepted_specs(self) -> list[DatasetSpec]:
        records = self.discover_catalog()
        accepted_names = {
            r.name for r in records if r.relevance_score >= self.min_relevance
        }
        return [s for s in self._catalog_specs() if s.name in accepted_names]

    def discover_directory(self) -> list[DatasetRecord]:
        """Scan raw data directory for any CSV files."""
        records: list[DatasetRecord] = []
        for path in sorted(self.raw_dir.glob("*.csv")):
            record = self.discover_local(path.name)
            if record:
                records.append(record)
        return records

    def download_csv(self, url: str, filename: str) -> AgentResult:
        """Download a CSV from a public URL (Checkpoint 2 expansion)."""
        dest = self.raw_dir / filename
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            dest.write_bytes(response.content)
            record = self.discover_local(filename)
            return AgentResult(
                agent="discovery",
                success=True,
                message=f"Downloaded {filename}",
                data={"record": record.__dict__ if record else {}},
            )
        except requests.RequestException as exc:
            logger.error("Download failed for %s: %s", url, exc)
            return AgentResult(
                agent="discovery",
                success=False,
                message=str(exc),
            )

    def run(self) -> AgentResult:
        from agents.metabase_client import sync_norp_datasets
        import os

        if os.getenv("METABASE_URL") and os.getenv("METABASE_AUTO_SYNC", "").lower() == "true":
            sync_norp_datasets()

        records = self.discover_catalog()
        accepted = [r for r in records if r.relevance_score >= self.min_relevance]
        rejected = [r for r in records if r.relevance_score < self.min_relevance]

        inventory = {
            "total_discovered": len(records),
            "accepted": [r.__dict__ for r in accepted],
            "rejected": [r.__dict__ for r in rejected],
        }
        save_json(inventory, self.raw_dir.parent / "discovery_inventory.json")

        return AgentResult(
            agent="discovery",
            success=len(accepted) > 0,
            message=f"Discovered {len(records)} datasets, {len(accepted)} accepted",
            data=inventory,
        )


if __name__ == "__main__":
    result = DiscoveryAgent().run()
    print(result.message)
