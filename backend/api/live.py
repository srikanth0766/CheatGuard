from time import monotonic

import cv2
import numpy as np
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.core.database import SessionLocal, get_db
from backend.models import Analysis

router = APIRouter(prefix="/api/live", tags=["live analysis"])


@router.post("/start")
def start(db: Session = Depends(get_db)):
    analysis = Analysis(video_path="live://camera", status="queued")
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return {"analysis_id": analysis.id, "status": analysis.status, "model": "sav-yolo"}


@router.websocket("/stream/{analysis_id}")
async def stream(websocket: WebSocket, analysis_id: int):
    await websocket.accept()
    with SessionLocal() as db:
        analysis = db.get(Analysis, analysis_id)
        if not analysis:
            await websocket.close(code=1008, reason="Analysis not found")
            return
        from ai_pipeline.per_person_sav_pipeline import SavPipeline
        pipeline = SavPipeline()
        pipeline.start_session()
        analysis.status = "running"
        db.commit()
        started = monotonic()
        try:
            while True:
                payload = await websocket.receive_bytes()
                frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                annotated = pipeline.process_frame(db, analysis, frame, monotonic() - started, 24)
                db.commit()
                ok, encoded = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 78])
                if ok:
                    await websocket.send_bytes(encoded.tobytes())
        except WebSocketDisconnect:
            analysis.status, analysis.progress = "completed", 100
            db.commit()
        except Exception as exc:
            analysis.status, analysis.error = "failed", str(exc)
            db.commit()
            await websocket.close(code=1011)
