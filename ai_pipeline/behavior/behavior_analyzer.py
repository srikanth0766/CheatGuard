class BehaviorAnalyzer:
    TEMPORAL = {"looking_around", "suspicious_interaction", "whispering", "passing_items"}

    def analyze(self, state, detected_behavior: str, confidence: float):
        if detected_behavior not in self.TEMPORAL:
            return detected_behavior, confidence
        recent = [b for _, b, _ in state.behavior_history][-8:]
        confirmations = recent.count(detected_behavior) + 1
        if confirmations < 3:
            return "normal", confidence
        return detected_behavior, confidence

