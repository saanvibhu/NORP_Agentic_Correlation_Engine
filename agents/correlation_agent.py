"""Agent 4: Correlation — statistical relationship discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.feature_selection import mutual_info_regression

from agents.base import DATA_PROCESSED, OUTPUTS_DIR, AgentResult, load_csv, save_json, setup_logger
from agents.dataset_registry import JOIN_KEY, REAL_DATASETS, STATE_KEY

logger = setup_logger(__name__)

MERGED_COUNTY_PATH = OUTPUTS_DIR / "merged_county.csv"


@dataclass
class CorrelationResult:
    variable_x: str
    variable_y: str
    pearson_r: float
    pearson_p: float
    spearman_r: float
    spearman_p: float
    mutual_information: float
    regression_coef: float | None = None
    regression_r_squared: float | None = None
    significant: bool = False

    def to_dict(self) -> dict:
        return {
            "variable_x": self.variable_x,
            "variable_y": self.variable_y,
            "pearson_r": self.pearson_r,
            "pearson_p": self.pearson_p,
            "spearman_r": self.spearman_r,
            "spearman_p": self.spearman_p,
            "mutual_information": self.mutual_information,
            "regression_coef": self.regression_coef,
            "regression_r_squared": self.regression_r_squared,
            "significant": self.significant,
        }


class CorrelationAgent:
    """Runs Pearson, Spearman, mutual information, and regression analysis."""

    def __init__(
        self,
        processed_dir: Path | None = None,
        significance_level: float = 0.05,
        min_abs_correlation: float = 0.3,
        use_real_data: bool = True,
        states: list[str] | None = None,
    ):
        self.processed_dir = processed_dir or DATA_PROCESSED
        self.significance_level = significance_level
        self.min_abs_correlation = min_abs_correlation
        self.use_real_data = use_real_data
        self.states = states

    def _pairwise_analysis(self, df: pd.DataFrame, col_x: str, col_y: str) -> CorrelationResult | None:
        subset = df[[col_x, col_y]].dropna()
        if len(subset) < 10:
            return None

        x = subset[col_x].values
        y = subset[col_y].values
        pearson_r, pearson_p = stats.pearsonr(x, y)
        spearman_r, spearman_p = stats.spearmanr(x, y)
        mi = mutual_info_regression(x.reshape(-1, 1), y, random_state=42)[0]

        x_const = sm.add_constant(x)
        model = sm.OLS(y, x_const).fit()
        coef = float(model.params[1]) if len(model.params) > 1 else None

        significant = (
            pearson_p < self.significance_level
            and abs(pearson_r) >= self.min_abs_correlation
        )

        return CorrelationResult(
            variable_x=col_x,
            variable_y=col_y,
            pearson_r=round(pearson_r, 4),
            pearson_p=round(pearson_p, 6),
            spearman_r=round(spearman_r, 4),
            spearman_p=round(spearman_p, 6),
            mutual_information=round(float(mi), 4),
            regression_coef=round(coef, 4) if coef is not None else None,
            regression_r_squared=round(float(model.rsquared), 4),
            significant=significant,
        )

    def analyze_dataframe(self, df: pd.DataFrame) -> list[CorrelationResult]:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        results: list[CorrelationResult] = []
        for i, col_x in enumerate(numeric_cols):
            for col_y in numeric_cols[i + 1 :]:
                result = self._pairwise_analysis(df, col_x, col_y)
                if result:
                    results.append(result)
        results.sort(key=lambda r: abs(r.pearson_r), reverse=True)
        return results

    def build_county_merged_frame(self, datasets: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
        """Merge IRS, Census, CDC, and volunteer data at county level."""
        irs_key = "irs_990_county"
        if irs_key not in datasets:
            return None

        merged = datasets[irs_key].copy()

        if "census_acs_dp03_county" in datasets:
            census = datasets["census_acs_dp03_county"].drop(
                columns=[c for c in ("county_name",) if c in datasets["census_acs_dp03_county"].columns],
                errors="ignore",
            )
            merged = merged.merge(census, on=[STATE_KEY, JOIN_KEY], how="left", suffixes=("", "_census"))

        if "cdc_places_county" in datasets:
            cdc = datasets["cdc_places_county"].drop(
                columns=[c for c in ("county_name",) if c in datasets["cdc_places_county"].columns],
                errors="ignore",
            )
            merged = merged.merge(cdc, on=[STATE_KEY, JOIN_KEY], how="left")

        if "volunteer_county" in datasets:
            vol = datasets["volunteer_county"]
            vol_cols = [c for c in vol.columns if c not in (STATE_KEY, JOIN_KEY, "county_name", "org_count")]
            merged = merged.merge(
                vol[[STATE_KEY, JOIN_KEY] + [c for c in vol_cols if c in vol.columns]],
                on=[STATE_KEY, JOIN_KEY],
                how="left",
                suffixes=("", "_vol"),
            )

        if self.states:
            merged = merged[merged[STATE_KEY].isin(self.states)]

        return merged if not merged.empty else None

    def correlation_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.select_dtypes(include="number").corr(method="pearson")

    def run(self) -> AgentResult:
        if self.use_real_data:
            paths = [self.processed_dir / s.processed_name for s in REAL_DATASETS]
            paths.append(self.processed_dir / "volunteer_county.csv")
        else:
            paths = sorted(self.processed_dir.glob("sample_*.csv"))

        paths = [p for p in paths if p.exists()]
        if not paths:
            return AgentResult(agent="correlation", success=False, message="No processed datasets found")

        datasets = {p.stem: load_csv(p) for p in paths}
        all_results: list[CorrelationResult] = []
        merged = None
        heatmap_df = None

        if self.use_real_data:
            merged = self.build_county_merged_frame(datasets)
            if merged is not None and not merged.empty:
                merged.to_csv(MERGED_COUNTY_PATH, index=False)
                all_results = self.analyze_dataframe(merged)
                heatmap_df = self.correlation_matrix(merged)
                logger.info(
                    "County-level merged analysis: %d counties, %d pairs",
                    len(merged),
                    len(all_results),
                )
        else:
            for name, df in datasets.items():
                all_results.extend(self.analyze_dataframe(df))
            if "sample_volunteer_engagement" in datasets and "sample_demographics" in datasets:
                merged = pd.merge(
                    datasets["sample_volunteer_engagement"],
                    datasets["sample_demographics"],
                    on="zip_code",
                    how="inner",
                )
                all_results.extend(self.analyze_dataframe(merged))
            heatmap_df = self.correlation_matrix(merged) if merged is not None else None

        significant = [r for r in all_results if r.significant]
        significant.sort(key=lambda r: abs(r.pearson_r), reverse=True)

        summary = {
            "mode": "real" if self.use_real_data else "sample",
            "states": self.states,
            "merged_counties": len(merged) if merged is not None else 0,
            "total_pairs_analyzed": len(all_results),
            "significant_findings": len(significant),
            "top_correlations": [r.to_dict() for r in significant[:20]],
            "all_correlations": [r.to_dict() for r in all_results],
            "correlation_matrix": heatmap_df.round(4).to_dict() if heatmap_df is not None else None,
            "suggested_scatter_pairs": [
                {"x": r.variable_x, "y": r.variable_y}
                for r in significant[:6]
            ],
        }
        save_json(summary, OUTPUTS_DIR / "correlations.json")

        return AgentResult(
            agent="correlation",
            success=bool(all_results),
            message=f"Found {len(significant)} significant correlations out of {len(all_results)} pairs",
            data=summary,
        )
