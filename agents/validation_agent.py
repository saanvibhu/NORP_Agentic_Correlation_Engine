"""Agent 3: Verification — quality scoring and join validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from agents.base import DATA_PROCESSED, AgentResult, load_csv, save_json, setup_logger
from agents.dataset_registry import JOIN_KEY, REAL_DATASETS, SAMPLE_DATASETS

logger = setup_logger(__name__)

DEFAULT_QUALITY_THRESHOLD = 70.0


@dataclass
class QualityReport:
    dataset_name: str
    quality_score: float
    missing_value_pct: float
    duplicate_count: int
    row_count: int
    column_count: int
    passed: bool
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dataset_name": self.dataset_name,
            "quality_score": self.quality_score,
            "missing_value_pct": self.missing_value_pct,
            "duplicate_count": self.duplicate_count,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "passed": self.passed,
            "issues": self.issues,
        }


class ValidationAgent:
    """Measures data quality, join success, and produces quality scores."""

    def __init__(
        self,
        processed_dir: Path | None = None,
        quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
        use_real_data: bool = True,
    ):
        self.processed_dir = processed_dir or DATA_PROCESSED
        self.quality_threshold = quality_threshold
        self.use_real_data = use_real_data

    def compute_quality_score(
        self,
        df: pd.DataFrame,
        duplicate_count: int = 0,
    ) -> tuple[float, list[str]]:
        issues: list[str] = []
        if df.empty:
            return 0.0, ["Dataset is empty"]

        missing_pct = df.isnull().mean().mean() * 100
        completeness_score = max(0, 100 - missing_pct * 2)

        dup_penalty = min(duplicate_count / max(len(df), 1) * 100, 30)
        uniqueness_score = max(0, 100 - dup_penalty)

        numeric_cols = df.select_dtypes(include="number").columns
        type_score = 100.0
        if len(numeric_cols) == 0 and len(df.columns) > 2:
            type_score = 70.0
            issues.append("No numeric columns for correlation analysis")

        score = completeness_score * 0.5 + uniqueness_score * 0.3 + type_score * 0.2
        score = round(min(score, 100), 1)

        if missing_pct > 20:
            issues.append(f"High missing values: {missing_pct:.1f}%")
        if duplicate_count > 0:
            issues.append(f"{duplicate_count} duplicate rows detected")

        return score, issues

    def validate_dataset(self, path: Path) -> QualityReport:
        df = load_csv(path)
        duplicate_count = int(df.duplicated().sum())
        missing_pct = round(df.isnull().mean().mean() * 100, 2)
        score, issues = self.compute_quality_score(df, duplicate_count)

        report = QualityReport(
            dataset_name=path.stem,
            quality_score=score,
            missing_value_pct=missing_pct,
            duplicate_count=duplicate_count,
            row_count=len(df),
            column_count=len(df.columns),
            passed=score >= self.quality_threshold,
            issues=issues,
        )
        status = "PASSED" if report.passed else "DROPPED"
        logger.info(
            "Validation %s — score=%.1f/100 [%s]",
            report.dataset_name,
            report.quality_score,
            status,
        )
        return report

    def join_success_rate(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        left_key: str,
        right_key: str,
    ) -> float:
        """Compute join match rate between two datasets."""
        if left_key not in left.columns or right_key not in right.columns:
            return 0.0
        left_keys = set(left[left_key].dropna().astype(str).unique())
        right_keys = set(right[right_key].dropna().astype(str).unique())
        if not left_keys:
            return 0.0
        matched = len(left_keys & right_keys)
        return round(matched / len(left_keys) * 100, 2)

    def run(self, filenames: list[str] | None = None) -> AgentResult:
        if filenames is None:
            if self.use_real_data:
                filenames = [s.processed_name for s in REAL_DATASETS] + ["volunteer_county.csv"]
            else:
                filenames = [
                    p.name for p in sorted(self.processed_dir.glob("sample_*.csv"))
                ]

        reports: list[QualityReport] = []
        accepted: list[str] = []
        dropped: list[str] = []

        for name in filenames:
            path = self.processed_dir / name
            if not path.exists():
                logger.warning("Skipping missing processed file: %s", name)
                continue
            report = self.validate_dataset(path)
            reports.append(report)
            if report.passed:
                accepted.append(name)
            else:
                dropped.append(name)

        join_metrics: dict[str, float] = {}
        loaded = {
            p.stem: load_csv(p)
            for p in self.processed_dir.glob("*.csv")
            if p.name in accepted or p.name in filenames
        }

        if self.use_real_data:
            keys = {
                "irs_990_county": JOIN_KEY,
                "census_acs_dp03_county": JOIN_KEY,
                "cdc_places_county": JOIN_KEY,
                "volunteer_county": JOIN_KEY,
            }
            if all(k in loaded for k in ("irs_990_county", "census_acs_dp03_county", "cdc_places_county")):
                irs, census, cdc = (
                    loaded["irs_990_county"],
                    loaded["census_acs_dp03_county"],
                    loaded["cdc_places_county"],
                )
                join_metrics["irs_to_census"] = self.join_success_rate(
                    irs, census, JOIN_KEY, JOIN_KEY
                )
                join_metrics["irs_to_cdc"] = self.join_success_rate(
                    irs, cdc, JOIN_KEY, JOIN_KEY
                )
                join_metrics["census_to_cdc"] = self.join_success_rate(
                    census, cdc, JOIN_KEY, JOIN_KEY
                )
        elif (
            "sample_volunteer_engagement" in loaded
            and "sample_demographics" in loaded
        ):
            join_metrics["volunteer_to_demographics"] = self.join_success_rate(
                loaded["sample_volunteer_engagement"],
                loaded["sample_demographics"],
                "zip_code",
                "zip_code",
            )

        summary = {
            "quality_threshold": self.quality_threshold,
            "reports": [r.to_dict() for r in reports],
            "accepted": accepted,
            "dropped": dropped,
            "join_metrics": join_metrics,
        }
        save_json(summary, self.processed_dir / "validation_report.json")

        return AgentResult(
            agent="validation",
            success=len(accepted) > 0,
            message=f"Validated {len(reports)} datasets — {len(accepted)} passed, {len(dropped)} dropped",
            data=summary,
        )


if __name__ == "__main__":
    result = ValidationAgent().run()
    print(result.message)
