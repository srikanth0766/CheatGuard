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

LABELS = ["sit", "stand", "look_forward", "look_sideways", "read", "flip_books",
          "touch_sth", "raise_hand", "hands_down", "take_notes", "applaud", "bend",
          "turn_around", "talk_with_others", "answer_questions"]
SUSPICION_INCREMENTS = {
    "look_sideways": 15,
    "bend": 20,
    "turn_around": 20,
    "talk_with_others": 35,
    "mobile_phone": 35,
}
SUSPICION_DECAY = 10


class SavPipeline:
    """YOLO/ByteTrack person tracking with per-person SAV MobileNet classification."""

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
        self.mapper = ClassroomMapper()

    def predict(self, crop):
        from PIL import Image
        image = self.transform(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))).unsqueeze(0)
        with self.torch.inference_mode():
            scores = self.model(image).sigmoid()[0]
        return sorted(((LABELS[i], float(score)) for i, score in enumerate(scores)),
                      key=lambda prediction: prediction[1], reverse=True)

    def start_session(self):
        self.states, self.students, self.display_labels = {}, {}, {}
        self.behaviors = SavBehaviorAnalyzer()
        self.alerts = AlertManager(settings.evidence_dir, settings.alert_threshold)
        self.last_sample_at = {}

    def process_frame(self, db, analysis, frame, timestamp, fps=24, recent_frames=()):
        height, width = frame.shape[:2]
        active = {}
        pending_alerts = []
        # COCO YOLO owns person localization: every person starts as normal.
        detections = self.detector.track(frame)
        phones_by_track = self.match_phones(detections, self.detector.phones)
        for detection in detections:
            tid, bbox = detection["track_id"], detection["bbox"]
            x1, y1, x2, y2 = bbox
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(width, x2), min(height, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            state = self.states.setdefault(tid, StudentState(tid, bbox, detection["confidence"]))
            active[tid] = state
            if tid not in self.students:
                student = Student(analysis_id=analysis.id, track_id=tid)
                db.add(student)
                db.flush()
                self.students[tid] = student
            student = self.students[tid]
            behavior, confidence, critical = "normal", detection["confidence"], False
            sampled = timestamp - self.last_sample_at.get(tid, -1) >= .5
            if sampled:
                self.last_sample_at[tid] = timestamp
                predictions = self.predict(frame[y1:y2, x1:x2])
                observed, behavior, confidence, critical = self.behaviors.analyze(tid, predictions)
                self.display_labels[tid] = observed
                if tid in phones_by_track:
                    behavior, confidence, critical = "mobile_phone", phones_by_track[tid], False
                if behavior != "normal":
                    state.risk_score = min(100, state.risk_score + SUSPICION_INCREMENTS[behavior] * confidence)
                    student.current_risk = round(state.risk_score, 2)
                    student.risk_level = "critical" if critical else risk_level(state.risk_score)
                    db.add(BehaviorEvent(student_id=student.id, behavior_type=behavior,
                                         confidence=confidence, video_timestamp=timestamp))
                    db.add(RiskScore(student_id=student.id, score=student.current_risk,
                                     risk_level=student.risk_level))
                else:
                    state.risk_score = max(0, state.risk_score - SUSPICION_DECAY)
                    student.current_risk = state.risk_score
                    student.risk_level = risk_level(state.risk_score)
            else:
                behavior = state.current_behavior
            state.update((x1, y1, x2, y2), confidence, timestamp, behavior)
            student.last_seen = datetime.utcnow()
            color = (0, 200, 0) if state.risk_score <= 20 else (0, 165, 255) if state.risk_score <= 50 else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            status = (state.current_behavior if state.current_behavior != "normal"
                      else self.display_labels.get(tid, "normal"))
            cv2.putText(frame, f"ID {tid} {status}", (x1, max(20, y1 - 7)),
                        cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
            if sampled and behavior != "normal" and (critical or state.risk_score > 20):
                pending_alerts.append((student, state, behavior, critical))
        for phone in self.detector.phones:
            px1, py1, px2, py2 = phone["bbox"]
            cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 255), 2)
            cv2.putText(frame, f"phone {phone['confidence']:.2f}", (px1, max(20, py1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 0, 255), 1)
        self.mapper.update(active, width, height)
        for tid, state in active.items():
            self.students[tid].seat_id = state.seat_id
        # Save evidence only after every person box has been drawn on this frame.
        for student, state, behavior, critical in pending_alerts:
            self.alerts.maybe_create(
                db, student, state, frame, timestamp, behavior, recent_frames, fps, force=True,
                reason=f"Critical malpractice: {behavior.replace('_', ' ')}" if critical else None)
        return frame

    @staticmethod
    def match_phones(detections, phones):
        matches = {}
        for phone in phones:
            x1, y1, x2, y2 = phone["bbox"]
            center = ((x1 + x2) / 2, (y1 + y2) / 2)
            candidates = [d for d in detections if d["bbox"][0] <= center[0] <= d["bbox"][2]
                          and d["bbox"][1] <= center[1] <= d["bbox"][3]]
            if candidates:
                owner = min(candidates, key=lambda d: (d["bbox"][2] - d["bbox"][0]) *
                            (d["bbox"][3] - d["bbox"][1]))
                matches[owner["track_id"]] = max(matches.get(owner["track_id"], 0), phone["confidence"])
        return matches

    def run(self, db, analysis: Analysis):
        capture = cv2.VideoCapture(analysis.video_path)
        if not capture.isOpened():
            raise ValueError("The uploaded file is not a readable video")
        fps = capture.get(cv2.CAP_PROP_FPS) or 25
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        output = Path(analysis.video_path).with_name(f"analyzed_{analysis.id}.mp4")
        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        recent_frames = deque(maxlen=max(1, int(fps * 2)))
        self.start_session()
        analysis.status = "running"
        db.commit()
        frame_number = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame = self.process_frame(db, analysis, frame, frame_number / fps, fps, recent_frames)
                writer.write(frame)
                recent_frames.append(frame.copy())
                frame_number += 1
                if frame_number % 10 == 0:
                    db.refresh(analysis)
                    if analysis.status == "cancelled":
                        return
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
