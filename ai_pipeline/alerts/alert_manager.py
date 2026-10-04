from pathlib import Path
import cv2
from backend.models import Alert, Evidence


class AlertManager:
    def __init__(self, evidence_dir: Path, threshold: float):
        self.frame_dir = evidence_dir / "frames"
        self.clip_dir = evidence_dir / "clips"
        self.frame_dir.mkdir(parents=True, exist_ok=True)
        self.clip_dir.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold
        self.last_alert_at: dict[tuple[int, str], float] = {}
        self.cooldown_seconds = 5

    def maybe_create(self, db, student, state, frame, timestamp, behavior, recent_frames=(), fps=25,
                     force=False, reason=None):
        key = (state.track_id, behavior)
        if (not force and state.risk_score < self.threshold) or timestamp - self.last_alert_at.get(key, -self.cooldown_seconds) < self.cooldown_seconds:
            return None
        alert = Alert(student_id=student.id, risk_score=state.risk_score, video_timestamp=timestamp,
                      reason=reason or f"{behavior.replace('_', ' ').title()} raised cumulative risk to {state.risk_score:.1f}")
        db.add(alert); db.flush()
        path = self.frame_dir / f"alert_{alert.id}_{timestamp:.2f}.jpg"
        cv2.imwrite(str(path), frame)
        clip_path = self.clip_dir / f"alert_{alert.id}_{timestamp:.2f}.mp4"
        frames = [*recent_frames, frame.copy()]
        if frames:
            height, width = frames[0].shape[:2]
            writer = cv2.VideoWriter(str(clip_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
            for evidence_frame in frames:
                writer.write(evidence_frame)
            writer.release()
        db.add(Evidence(alert_id=alert.id, frame_path=str(path), clip_path=str(clip_path)))
        self.last_alert_at[key] = timestamp
        return alert
