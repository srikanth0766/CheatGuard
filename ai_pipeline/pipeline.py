from datetime import datetime
from pathlib import Path
from collections import deque
import cv2
from backend.core.config import settings
from backend.models import Analysis, BehaviorEvent, RiskScore, Student
from ai_pipeline.alerts.alert_manager import AlertManager
from ai_pipeline.behavior.behavior_analyzer import BehaviorAnalyzer
from ai_pipeline.detection.student_detector import StudentDetector
from ai_pipeline.mapping.classroom_mapper import ClassroomMapper
from ai_pipeline.pose.pose_estimator import PoseEstimator
from ai_pipeline.risk.risk_scorer import RiskScorer, risk_level
from ai_pipeline.state.student_state import StudentState
from ai_pipeline.video_output import make_browser_compatible


class VideoPipeline:
    def __init__(self):
        self.detector = StudentDetector()
        self.pose = PoseEstimator()
        self.mapper = ClassroomMapper()
        self.behaviors = BehaviorAnalyzer()
        self.risk = RiskScorer()

    def run(self, db, analysis: Analysis):
        capture = cv2.VideoCapture(analysis.video_path)
        if not capture.isOpened(): raise ValueError("The uploaded file is not a readable video")
        fps = capture.get(cv2.CAP_PROP_FPS) or 25
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        output = Path(analysis.video_path).with_name(f"analyzed_{analysis.id}.mp4")
        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        states, students = {}, {}
        alerts = AlertManager(settings.evidence_dir, settings.alert_threshold)
        recent_frames = deque(maxlen=max(1, int(fps * 2)))
        analysis.status = "running"; db.commit()
        frame_number = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok: break
                timestamp = frame_number / fps
                for detection in self.detector.track(frame):
                    tid, bbox = detection["track_id"], detection["bbox"]
                    state = states.setdefault(tid, StudentState(tid, bbox, detection["confidence"]))
                    behavior, confidence = self.behaviors.analyze(state, detection["behavior"], detection["confidence"])
                    pose = self.pose.estimate(frame, bbox)
                    state.update(bbox, confidence, timestamp, behavior, pose)
                    if tid not in students:
                        student = Student(analysis_id=analysis.id, track_id=tid)
                        db.add(student); db.flush(); students[tid] = student
                    student = students[tid]
                    if behavior != "normal":
                        score = self.risk.update(state, behavior, confidence)
                        level = risk_level(score)
                        student.current_risk, student.risk_level = score, level
                        db.add(BehaviorEvent(student_id=student.id, behavior_type=behavior, confidence=confidence,
                                             video_timestamp=timestamp))
                        db.add(RiskScore(student_id=student.id, score=score, risk_level=level))
                    student.last_seen = datetime.utcnow()
                    color = (0, 200, 0) if state.risk_score <= 20 else (0, 165, 255) if state.risk_score <= 50 else (0, 0, 255)
                    x1, y1, x2, y2 = bbox
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"ID {tid} {behavior} {state.risk_score:.0f}", (x1, max(20, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
                    if behavior != "normal":
                        alerts.maybe_create(db, student, state, frame, timestamp, behavior, recent_frames, fps)
                self.mapper.update(states, width, height)
                for tid, student in students.items():
                    if tid in states:
                        student.seat_id = states[tid].seat_id
                writer.write(frame); frame_number += 1
                recent_frames.append(frame.copy())
                if frame_number % 30 == 0:
                    analysis.progress = min(99, frame_number / total * 100); db.commit()
            writer.release()
            make_browser_compatible(output)
            analysis.output_path, analysis.status, analysis.progress = str(output), "completed", 100
            db.commit()
        except Exception as exc:
            analysis.status, analysis.error = "failed", str(exc); db.commit(); raise
        finally:
            capture.release(); writer.release()
