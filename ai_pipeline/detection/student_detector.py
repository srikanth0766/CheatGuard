from pathlib import Path

from backend.core.config import settings

TRACKER = Path(__file__).with_name("bytetrack_all.yaml")


class StudentDetector:
    def __init__(self):
        from ultralytics import YOLO
        if not settings.person_model_path.exists():
            raise FileNotFoundError(f"Person model not found: {settings.person_model_path}")
        self.model = YOLO(settings.person_model_path)

    def track(self, frame, imgsz=1280):
        result = self.model.track(frame, persist=True, tracker=str(TRACKER),
                                  conf=settings.person_detection_confidence,
                                  classes=[0, 67], imgsz=imgsz, verbose=False)[0]
        detections = []
        self.phones = []
        if result.boxes is None or result.boxes.id is None:
            return detections
        for xyxy, track_id, cls_id, conf in zip(result.boxes.xyxy, result.boxes.id, result.boxes.cls, result.boxes.conf):
            bbox = tuple(int(v) for v in xyxy.tolist())
            if int(cls_id) == 67:
                if float(conf) > settings.phone_detection_confidence:
                    self.phones.append({"bbox": bbox, "confidence": float(conf)})
                continue
            detections.append({
                "bbox": bbox,
                "track_id": int(track_id),
                "class_id": int(cls_id),
                "behavior": "person",
                "confidence": float(conf),
            })
        return detections
