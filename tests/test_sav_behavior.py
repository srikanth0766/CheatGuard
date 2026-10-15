import pytest

from ai_pipeline.behavior.sav_behavior_analyzer import SavBehaviorAnalyzer


def test_normal_exam_actions_are_not_malpractice():
    analyzer = SavBehaviorAnalyzer()
    for _ in range(4):
        assert analyzer.analyze(1, [("sit", .9), ("read", .8), ("take_notes", .7)])[1] == "normal"


def test_repeated_sideways_looking_is_confirmed_per_student():
    analyzer = SavBehaviorAnalyzer()
    assert analyzer.analyze(7, [("look_sideways", .8)])[1] == "normal"
    assert analyzer.analyze(7, [("look_sideways", .8)])[1] == "normal"
    observed, behavior, confidence, critical = analyzer.analyze(7, [("look_sideways", .8)])
    assert (observed, behavior) == ("look_sideways", "look_sideways")
    assert confidence == pytest.approx(.8)
    assert critical is False
    assert analyzer.analyze(8, [("look_forward", .9)])[1] == "normal"


def test_talking_is_critical_and_ignored_classes_do_nothing():
    analyzer = SavBehaviorAnalyzer()
    assert analyzer.analyze(2, [("touch_sth", .99)])[1] == "normal"
    assert analyzer.analyze(2, [("stand", .99)])[1] == "normal"
    analyzer.analyze(2, [("talk_with_others", .9)])
    assert analyzer.analyze(2, [("talk_with_others", .9)])[1:] == (
        "talk_with_others", pytest.approx(.9), True)
