from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
model = YOLO(ROOT / "best_large.pt")
metrics = model.val(data=ROOT / "classroom.v1i.yolo26 " / "data.yaml", split="test", project=ROOT / "cheatguard/evaluation", name="test")
print({"precision": float(metrics.box.mp), "recall": float(metrics.box.mr), "mAP50": float(metrics.box.map50), "mAP50-95": float(metrics.box.map)})
