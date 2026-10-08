from collections import defaultdict, deque


NORMAL = {"sit", "look_forward", "take_notes"}
MALPRACTICE_RULES = {
    "look_sideways": (3, 4, False),
    "bend": (3, 4, False),
    "talk_with_others": (2, 3, True),
}


class SavBehaviorAnalyzer:
    """Confirm per-person SAV predictions over time and map them to risk rules."""

    def __init__(self):
        self.history = defaultdict(lambda: deque(maxlen=4))

    def analyze(self, track_id: int, predictions: list[tuple[str, float]]):
        scores = dict(predictions)
        self.history[track_id].append(scores)
        relevant = NORMAL | MALPRACTICE_RULES.keys()
        visible = [(label, score) for label, score in predictions if label in relevant and score >= .5]
        observed = max(visible, key=lambda prediction: prediction[1])[0] if visible else "normal"
        matches = []
        for label, (required, window, critical) in MALPRACTICE_RULES.items():
            recent = list(self.history[track_id])[-window:]
            confirmed = [sample[label] for sample in recent if sample.get(label, 0) >= .5]
            if len(confirmed) >= required:
                matches.append((label, sum(confirmed) / len(confirmed), critical))
        if not matches:
            return observed, "normal", 0.0, False
        label, confidence, critical = max(matches, key=lambda match: match[1])
        return observed, label, confidence, critical
