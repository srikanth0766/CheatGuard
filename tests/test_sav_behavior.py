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
    assert (observed, behavior) == ("normal", "look_sideways")
    assert confidence == pytest.approx(.8)
    assert critical is False
    assert analyzer.analyze(8, [("look_forward", .9)])[1] == "normal"


def test_talking_is_critical_and_unflagged_classes_do_nothing():
    analyzer = SavBehaviorAnalyzer()
    assert analyzer.analyze(2, [("touch_sth", .99)])[1] == "normal"
    analyzer.analyze(2, [("talk_with_others", .9)])
    assert analyzer.analyze(2, [("talk_with_others", .9)])[1:] == (
        "talk_with_others", pytest.approx(.9), True)


@pytest.mark.parametrize("label,confidence", [
    ("look_sideways", .41), ("bend", .86), ("turn_around", .91),
])
def test_configured_classes_are_flags(label, confidence):
    analyzer = SavBehaviorAnalyzer()
    assert analyzer.analyze(3, [(label, confidence)])[1] == "normal"
    assert analyzer.analyze(3, [(label, confidence)])[1] == "normal"
    assert analyzer.analyze(3, [(label, confidence)])[1] == label


@pytest.mark.parametrize("label,confidence", [
    ("look_sideways", .39), ("bend", .84),
    ("turn_around", .89), ("talk_with_others", .69),
])
def test_below_threshold_is_not_flagged(label, confidence):
    analyzer = SavBehaviorAnalyzer()
    for _ in range(4):
        assert analyzer.analyze(4, [(label, confidence)])[1] == "normal"


def test_hands_down_is_not_flagged():
    analyzer = SavBehaviorAnalyzer()
    for _ in range(4):
        assert analyzer.analyze(5, [("hands_down", .99)])[1] == "normal"


def test_stand_is_not_flagged():
    analyzer = SavBehaviorAnalyzer()
    for _ in range(4):
        assert analyzer.analyze(5, [("stand", .99)])[1] == "normal"


@pytest.mark.parametrize("label", ["raise_hand"])
def test_removed_classes_are_not_flagged(label):
    analyzer = SavBehaviorAnalyzer()
    for _ in range(4):
        assert analyzer.analyze(6, [(label, .99)])[1] == "normal"


def test_look_forward_is_display_only_at_threshold():
    analyzer = SavBehaviorAnalyzer()
    assert analyzer.analyze(7, [("look_forward", .74)])[:2] == ("normal", "normal")
    assert analyzer.analyze(7, [("look_forward", .75)])[:2] == ("look_forward", "normal")
