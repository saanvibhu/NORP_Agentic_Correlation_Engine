import pandas as pd

from agents.config import PipelineConfig
from agents.validation_agent import ValidationAgent


def test_valid_dataset_is_accepted(tmp_path):
    path = tmp_path / "valid.csv"
    pd.DataFrame({"x": range(12), "y": range(12)}).to_csv(path, index=False)
    report = ValidationAgent(processed_dir=tmp_path, use_real_data=False).validate_dataset(path)
    assert report.passed
    assert report.failure_reasons == []


def test_low_quality_dataset_is_rejected(tmp_path):
    path = tmp_path / "poor.csv"
    pd.DataFrame({"x": [1, None], "y": [1, None]}).to_csv(path, index=False)
    config = PipelineConfig(minimum_rows=10, maximum_missing_percentage=10.0)
    report = ValidationAgent(processed_dir=tmp_path, use_real_data=False, config=config).validate_dataset(path)
    assert not report.passed
    assert report.failure_reasons
    assert report.recommended_corrective_action
