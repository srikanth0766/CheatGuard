from types import SimpleNamespace
from ai_pipeline.risk.risk_scorer import RiskScorer, risk_level


def test_risk_is_weighted_and_capped():
    state = SimpleNamespace(risk_score=0, behavior_history=[])
    scorer = RiskScorer()
    assert scorer.update(state, "mobile_phone", 1) == 30
    for _ in range(10): scorer.update(state, "passing_items", 1)
    assert state.risk_score == 100
    assert risk_level(state.risk_score) == "critical"


def test_normal_does_not_raise_risk():
    state = SimpleNamespace(risk_score=12, behavior_history=[])
    assert RiskScorer().update(state, "normal", 1) == 12

