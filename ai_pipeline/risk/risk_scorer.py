WEIGHTS = {
    "normal": 0,
    "looking_around": 10,
    "suspicious_interaction": 15,
    "whispering": 15,
    "hands_under_desk": 20,
    "mobile_phone": 30,
    "passing_items": 30,
}


def risk_level(score: float) -> str:
    if score <= 20: return "low"
    if score <= 50: return "medium"
    if score <= 75: return "high"
    return "critical"


class RiskScorer:
    def update(self, state, behavior: str, confidence: float, duration: float = 0) -> float:
        if behavior == "normal":
            return state.risk_score
        recent = sum(1 for _, b, _ in state.behavior_history if b == behavior)
        frequency = min(1.5, 1 + recent * 0.05)
        duration_factor = min(2.0, 1 + duration / 10)
        state.risk_score = min(100, state.risk_score + WEIGHTS.get(behavior, 0) * confidence * frequency * duration_factor)
        return round(state.risk_score, 2)

