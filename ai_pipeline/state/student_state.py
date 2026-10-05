from collections import deque
from dataclasses import dataclass, field


@dataclass
class StudentState:
    track_id: int
    bbox: tuple[int, int, int, int]
    confidence: float
    current_behavior: str = "normal"
    risk_score: float = 0
    seat_id: str | None = None
    neighbor_ids: list[int] = field(default_factory=list)
    pose: list = field(default_factory=list)
    position_history: deque = field(default_factory=lambda: deque(maxlen=90))
    pose_history: deque = field(default_factory=lambda: deque(maxlen=90))
    behavior_history: deque = field(default_factory=lambda: deque(maxlen=300))
    last_seen: float = 0

    def update(self, bbox, confidence, timestamp, behavior="normal", pose=None):
        self.bbox, self.confidence, self.last_seen = bbox, confidence, timestamp
        self.current_behavior = behavior
        self.pose = pose or []
        self.position_history.append((timestamp, bbox))
        self.pose_history.append((timestamp, self.pose))
        self.behavior_history.append((timestamp, behavior, confidence))

