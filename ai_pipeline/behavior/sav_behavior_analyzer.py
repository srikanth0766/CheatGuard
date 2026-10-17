from collections import defaultdict, deque


MALPRACTICE_RULES = {
    "look_sideways": (3, 4, .40, False),
    "bend": (3, 4, .85, False),
    "turn_around": (3, 4, .90, False),
    "talk_with_others": (2, 3, .70, True),
}
LOOK_FORWARD_THRESHOLD = .75


class SavBehaviorAnalyzer:
    """Confirm per-person SAV predictions over time and map them to risk rules."""

    def __init__(self):
        self.history = defaultdict(lambda: deque(maxlen=4))

    def analyze(self, track_id: int, predictions: list[tuple[str, float]]):
        scores = dict(predictions)
        self.history[track_id].append(scores)
        observed = "look_forward" if scores.get("look_forward", 0) >= LOOK_FORWARD_THRESHOLD else "normal"
        matches = []
        for label, (required, window, threshold, critical) in MALPRACTICE_RULES.items():
            recent = list(self.history[track_id])[-window:]
            confirmed = [sample[label] for sample in recent if sample.get(label, 0) >= threshold]
            if len(confirmed) >= required:
                matches.append((label, sum(confirmed) / len(confirmed), critical))
        if not matches:
            return observed, "normal", 0.0, False
        label, confidence, critical = max(matches, key=lambda match: match[1])
        return observed, label, confidence, critical
