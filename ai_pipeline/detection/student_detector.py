from backend.core.config import settings


class StudentDetector:
    def __init__(self):
        from ultralytics import YOLO
        if not settings.model_path.exists():
            raise FileNotFoundError(f"Model not found: {settings.model_path}")
        self.model = YOLO(settings.model_path)

    def track(self, frame, imgsz=640):
        result = self.model.track(frame, persist=True, tracker="bytetrack.yaml", conf=settings.detection_confidence,
                                  imgsz=imgsz, verbose=False)[0]
        detections = []
        if result.boxes is None or result.boxes.id is None:
            return detections
        for xyxy, track_id, cls_id, conf in zip(result.boxes.xyxy, result.boxes.id, result.boxes.cls, result.boxes.conf):
            detections.append({
                "bbox": tuple(int(v) for v in xyxy.tolist()),
                "track_id": int(track_id),
                "class_id": int(cls_id),
                "behavior": settings.labels.get(int(cls_id), f"class_{int(cls_id)}"),
                "confidence": float(conf),
            })
        return detections
