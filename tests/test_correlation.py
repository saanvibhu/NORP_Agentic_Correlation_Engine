import pandas as pd

from agents.correlation_agent import CorrelationAgent


def test_correlation_metrics_and_sample_size():
    frame = pd.DataFrame({"x": range(20), "y": [value * 3 for value in range(20)]})
    result = CorrelationAgent(use_real_data=False).analyze_dataframe(frame)[0]
    assert result.sample_size == 20
    assert result.pearson_r == 1.0
    assert result.spearman_r == 1.0
    assert result.significant


def test_insignificant_relationship_is_filtered():
    frame = pd.DataFrame({"x": range(20), "y": [1, 0] * 10})
    result = CorrelationAgent(use_real_data=False).analyze_dataframe(frame)[0]
    assert not result.significant


def test_empty_or_short_data_is_stable():
    frame = pd.DataFrame({"x": [1], "y": [2]})
    assert CorrelationAgent(use_real_data=False).analyze_dataframe(frame) == []
