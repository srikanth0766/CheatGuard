from types import SimpleNamespace
from ai_pipeline.behavior.behavior_analyzer import BehaviorAnalyzer
from ai_pipeline.alerts.alert_manager import AlertManager


def test_temporal_behavior_needs_three_observations():
    analyzer = BehaviorAnalyzer()
    state = SimpleNamespace(behavior_history=[(0, "looking_around", .8), (1, "looking_around", .8)])
    assert analyzer.analyze(state, "looking_around", .8)[0] == "looking_around"


def test_alert_cooldown_is_per_behavior(tmp_path):
    manager = AlertManager(tmp_path, 51)
    manager.last_alert_at[(4, "mobile_phone")] = 10
    assert 12 - manager.last_alert_at[(4, "mobile_phone")] < manager.cooldown_seconds
    assert (4, "passing_items") not in manager.last_alert_at
