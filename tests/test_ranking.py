from agents.ranking_agent import RankingAgent


def test_ranking_orders_by_strength_and_evidence():
    rows = [
        {"variable_x": "weak_a", "variable_y": "weak_b", "pearson_r": 0.5, "pearson_p": 0.01, "sample_size": 20, "significant": True},
        {"variable_x": "strong_a", "variable_y": "strong_b", "pearson_r": -0.9, "pearson_p": 0.001, "sample_size": 40, "significant": True},
        {"variable_x": "rejected_a", "variable_y": "rejected_b", "pearson_r": 0.99, "pearson_p": 0.0, "sample_size": 40, "significant": False},
    ]
    ranked = RankingAgent().rank_findings(rows, [{"quality_score": 90, "missing_value_pct": 2, "passed": True}])
    assert len(ranked) == 2
    assert ranked[0]["variable_1"] == "strong_a"
    assert ranked[0]["rank"] == 1


def test_empty_ranking_is_stable():
    assert RankingAgent().rank_findings([]) == []
