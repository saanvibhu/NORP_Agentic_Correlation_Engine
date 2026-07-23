import pandas as pd

from agents.cleaning_agent import CleaningAgent


def test_duplicate_removal_and_missing_handling():
    frame = pd.DataFrame({"name": ["A", "A", "B"], "value": [1.0, 1.0, None], "mostly_missing": [None, None, 1.0]})
    cleaned, report = CleaningAgent(use_real_data=False).clean(frame)
    assert len(cleaned) == 2
    assert cleaned["value"].isna().sum() == 1
    assert "mostly_missing" not in cleaned
    assert report["duplicates_removed"] == 1
