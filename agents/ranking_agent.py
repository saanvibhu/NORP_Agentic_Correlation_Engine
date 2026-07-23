"""Deterministic ranking of validated, significant correlation findings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.base import DATA_PROCESSED, OUTPUTS_DIR, AgentResult, save_json, setup_logger
from agents.config import PipelineConfig, load_config

logger = setup_logger(__name__)
RANKED_PATH = OUTPUTS_DIR / "ranked_correlations.json"


class RankingAgent:
    """Rank approved findings using strength, evidence, and data quality."""

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or load_config()

    @staticmethod
    def _confidence(correlation: float, p_value: float | None, sample_size: int) -> str:
        if p_value is not None and p_value <= 0.01 and abs(correlation) >= 0.7 and sample_size >= 30:
            return "high"
        if p_value is not None and p_value <= 0.05 and abs(correlation) >= 0.5:
            return "moderate"
        return "low"

    def rank_findings(self, correlations: list[dict[str, Any]], validation_reports: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        reports = validation_reports or []
        passed = [item for item in reports if item.get("passed")]
        quality_score = round(sum(float(item.get("quality_score", 0)) for item in passed) / len(passed), 2) if passed else 0.0
        missing_rate = round(sum(float(item.get("missing_value_pct", 100)) for item in passed) / len(passed), 2) if passed else 100.0
        scored = []
        seen_pairs: set[tuple[str, str]] = set()
        for item in correlations:
            if item.get("significant") is not True:
                continue
            coefficient = float(item.get("pearson_r", item.get("correlation_coefficient", 0)))
            variable_1 = item.get("variable_x", item.get("variable_1"))
            variable_2 = item.get("variable_y", item.get("variable_2"))
            pair = tuple(sorted((str(variable_1), str(variable_2))))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            p_value = item.get("pearson_p", item.get("p_value"))
            p_value = float(p_value) if p_value is not None else None
            sample_size = int(item.get("sample_size", item.get("n", 0)))
            score = (0.45 * abs(coefficient) + 0.2 * max(0.0, 1.0 - (p_value or 1.0)) + 0.15 * min(sample_size / max(self.config.minimum_sample_size * 3, 1), 1.0) + 0.15 * quality_score / 100 + 0.05 * max(0.0, 1.0 - missing_rate / 100))
            result = {
                "rank": 0,
                "variable_1": variable_1,
                "variable_2": variable_2,
                "correlation_coefficient": coefficient,
                "p_value": p_value,
                "sample_size": sample_size,
                "quality_score": quality_score,
                "missing_data_rate": missing_rate,
                "confidence_category": RankingAgent._confidence(coefficient, p_value, sample_size),
                "explanation": f"Rank reflects absolute strength {abs(coefficient):.2f}, p-value {p_value}, n={sample_size}, quality {quality_score:.1f}/100, and missingness {missing_rate:.1f}%.",
                "significant": True,
                "_score": score,
            }
            scored.append(result)
        scored.sort(key=lambda item: (-item["_score"], item["variable_1"] or "", item["variable_2"] or ""))
        for rank, result in enumerate(scored[: self.config.top_ranked_findings], 1):
            result["rank"] = rank
            result.pop("_score", None)
        return scored[: self.config.top_ranked_findings]

    def run(self, correlations_path: Path | None = None, validation_path: Path | None = None) -> AgentResult:
        correlation_path = correlations_path or (OUTPUTS_DIR / "correlations.json")
        report_path = validation_path or (DATA_PROCESSED / "validation_report.json")
        if not correlation_path.exists():
            return AgentResult(agent="ranking", success=False, message=f"Correlations file not found: {correlation_path}")
        try:
            correlations = json.loads(correlation_path.read_text(encoding="utf-8"))
            validation = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            ranked = self.rank_findings(correlations.get("all_correlations", []), validation.get("reports", []))
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error("Ranking failed: %s", exc)
            return AgentResult(agent="ranking", success=False, message=f"Ranking failed: {exc}")
        payload = {"ranked_correlations": ranked, "finding_count": len(ranked)}
        save_json(payload, RANKED_PATH)
        return AgentResult(agent="ranking", success=True, message=f"Ranked {len(ranked)} approved correlations", data=payload)
