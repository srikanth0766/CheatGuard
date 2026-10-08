from collections import deque
from datetime import datetime
from pathlib import Path

import cv2

from backend.core.config import settings
from backend.models import Analysis, BehaviorEvent, RiskScore, Student
from ai_pipeline.alerts.alert_manager import AlertManager
from ai_pipeline.behavior.sav_behavior_analyzer import SavBehaviorAnalyzer
from ai_pipeline.detection.student_detector import StudentDetector
from ai_pipeline.mapping.classroom_mapper import ClassroomMapper
from ai_pipeline.risk.risk_scorer import risk_level
from ai_pipeline.state.student_state import StudentState
from ai_pipeline.video_output import make_browser_compatible


LABELS = [
    "sit", "stand", "look_forward", "look_sideways", "read", "flip_books",
    "touch_sth", "raise_hand", "hands_down", "take_notes", "applaud", "bend",
    "turn_around", "talk_with_others", "answer_questions",
]
SUSPICION_INCREMENTS = {"look_sideways": 15, "bend": 20, "talk_with_others": 35}
SUSPICION_DECAY = 10


class SavPipeline:
    """Track each person, then classify and score their SAV behavior over time."""

    def __init__(self):
        import torch
        from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

        if not settings.sav_model_path.exists():
            raise FileNotFoundError(f"Model not found: {settings.sav_model_path}")
        checkpoint = torch.load(settings.sav_model_path, map_location="cpu", weights_only=False)
        self.model = mobilenet_v3_small(weights=None)
        self.model.classifier[-1] = torch.nn.Linear(self.model.classifier[-1].in_features, len(LABELS))
        self.model.load_state_dict(checkpoint["model"])
        self.model.eval()
        self.transform = MobileNet_V3_Small_Weights.DEFAULT.transforms()
        self.torch = torch
        self.detector = StudentDetector()
        self.behaviors = SavBehaviorAnalyzer()
        self.mapper = ClassroomMapper()

    def predict(self, crop):
        from PIL import Image

        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        image = self.transform(Image.fromarray(rgb)).unsqueeze(0)
        with self.torch.inference_mode():
            scores = self.model(image).sigmoid()[0]
        return sorted(((LABELS[i], float(score)) for i, score in enumerate(scores)),
                      key=lambda prediction: prediction[1], reverse=True)

    def run(self, db, analysis: Analysis):
        capture = cv2.VideoCapture(analysis.video_path)
        if not capture.isOpened():
            raise ValueError("The uploaded file is not a readable video")
        fps = capture.get(cv2.CAP_PROP_FPS) or 25
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        output = Path(analysis.video_path).with_name(f"analyzed_{analysis.id}.mp4")
        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        states, students, labels = {}, {}, {}
        alerts = AlertManager(settings.evidence_dir, settings.alert_threshold)
        recent_frames = deque(maxlen=max(1, int(fps * 2)))
        sample_every = max(1, round(fps / 2))
        analysis.status = "running"
        db.commit()
        frame_number = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                timestamp = frame_number / fps
                active = {}
                for detection in self.detector.track(frame):
                    tid, bbox = detection["track_id"], detection["bbox"]
                    x1, y1, x2, y2 = bbox
                    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(width, x2), min(height, y2)
                    if x2 <= x1 or y2 <= y1:
                        continue
                    state = states.setdefault(tid, StudentState(tid, bbox, detection["confidence"]))
                    active[tid] = state
                    if tid not in students:
                        student = Student(analysis_id=analysis.id, track_id=tid)
                        db.add(student)
                        db.flush()
                        students[tid] = student
                    student = students[tid]
                    behavior, confidence = "normal", detection["confidence"]
                    critical = False
                    if frame_number % sample_every == 0:
                        predictions = self.predict(frame[y1:y2, x1:x2])
                        observed, behavior, confidence, critical = self.behaviors.analyze(tid, predictions)
                        labels[tid] = observed
                        if behavior != "normal":
                            state.risk_score = min(100, state.risk_score + SUSPICION_INCREMENTS[behavior] * confidence)
                            student.current_risk = round(state.risk_score, 2)
                            student.risk_level = "critical" if critical else risk_level(state.risk_score)
                            db.add(BehaviorEvent(student_id=student.id, behavior_type=behavior,
                                                 confidence=confidence, video_timestamp=timestamp))
                            db.add(RiskScore(student_id=student.id, score=student.current_risk,
                                             risk_level=student.risk_level))
                        elif observed == "normal" or observed in {"sit", "look_forward", "take_notes"}:
                            state.risk_score = max(0, state.risk_score - SUSPICION_DECAY)
                            student.current_risk = state.risk_score
                            student.risk_level = risk_level(state.risk_score)
                    else:
                        behavior = state.current_behavior
                    state.update((x1, y1, x2, y2), confidence, timestamp, behavior)
                    student.last_seen = datetime.utcnow()
                    color = (0, 200, 0) if state.risk_score <= 20 else (0, 165, 255) if state.risk_score <= 50 else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    status = f"FLAG {behavior}" if state.current_behavior != "normal" else labels.get(tid, "observing")
                    cv2.putText(frame, f"ID {tid} {status}",
                                (x1, max(20, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
                    if frame_number % sample_every == 0 and behavior != "normal":
                        alerts.maybe_create(
                            db, student, state, frame, timestamp, behavior, recent_frames, fps,
                            force=critical,
                            reason=(f"Critical malpractice: {behavior.replace('_', ' ')}"
                                    if critical else None),
                        )
                self.mapper.update(active, width, height)
                for tid, state in active.items():
                    students[tid].seat_id = state.seat_id
                writer.write(frame)
                recent_frames.append(frame.copy())
                frame_number += 1
                if frame_number % 30 == 0:
                    analysis.progress = min(99, frame_number / total * 100)
                    db.commit()
            writer.release()
            make_browser_compatible(output)
            analysis.output_path, analysis.status, analysis.progress = str(output), "completed", 100
            db.commit()
        except Exception as exc:
            analysis.status, analysis.error = "failed", str(exc)
            db.commit()
            raise
        finally:
            capture.release()
            writer.release()
