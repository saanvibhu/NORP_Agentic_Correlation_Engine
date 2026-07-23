"""Configuration loading with deterministic defaults."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


@dataclass(frozen=True)
class PipelineConfig:
    minimum_rows: int = 10
    maximum_missing_percentage: float = 20.0
    maximum_duplicate_percentage: float = 10.0
    minimum_join_success_rate: float = 70.0
    minimum_correlation_magnitude: float = 0.3
    significance_threshold: float = 0.05
    minimum_sample_size: int = 10
    top_ranked_findings: int = 20

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: Path | None = None) -> PipelineConfig:
    """Load valid YAML values, falling back to safe defaults."""
    config_path = path or CONFIG_PATH
    defaults = PipelineConfig()
    try:
        with config_path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        if not isinstance(raw, dict):
            return defaults
        values = defaults.to_dict()
        for key in values:
            if key in raw and isinstance(raw[key], (int, float)) and not isinstance(raw[key], bool):
                values[key] = raw[key]
        values["minimum_rows"] = max(1, int(values["minimum_rows"]))
        values["minimum_sample_size"] = max(2, int(values["minimum_sample_size"]))
        values["top_ranked_findings"] = max(1, int(values["top_ranked_findings"]))
        values["maximum_missing_percentage"] = min(100.0, max(0.0, float(values["maximum_missing_percentage"])))
        values["maximum_duplicate_percentage"] = min(100.0, max(0.0, float(values["maximum_duplicate_percentage"])))
        values["minimum_join_success_rate"] = min(100.0, max(0.0, float(values["minimum_join_success_rate"])))
        values["minimum_correlation_magnitude"] = min(1.0, max(0.0, float(values["minimum_correlation_magnitude"])))
        values["significance_threshold"] = min(1.0, max(0.0, float(values["significance_threshold"])))
        return PipelineConfig(**values)
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        return defaults
