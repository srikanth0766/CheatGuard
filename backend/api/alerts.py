from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from backend.core.database import get_db
from backend.models import Alert, Evidence, Student

router = APIRouter(prefix="/api", tags=["alerts"])


def serialize(alert, db):
    student = db.get(Student, alert.student_id)
    return {"id": alert.id, "student_id": alert.student_id,
            "track_id": student.track_id if student else None, "risk_score": alert.risk_score,
            "reason": alert.reason, "video_timestamp": alert.video_timestamp, "status": alert.status,
            "created_at": alert.created_at, "evidence": [{"id": e.id, "frame_url": f"/api/evidence/{e.id}",
            "clip_url": f"/api/evidence/{e.id}/clip" if e.clip_path else None} for e in alert.evidence]}


@router.get("/alerts")
def alerts(db: Session = Depends(get_db)):
    rows = db.scalars(select(Alert).options(selectinload(Alert.evidence)).order_by(Alert.created_at.desc())).all()
    return [serialize(row, db) for row in rows if row.risk_score > 20]


@router.get("/alerts/{alert_id}")
def alert(alert_id: int, db: Session = Depends(get_db)):
    row = db.scalar(select(Alert).options(selectinload(Alert.evidence)).where(Alert.id == alert_id))
    if not row: raise HTTPException(404, "Alert not found")
    return serialize(row, db)


@router.get("/evidence/{evidence_id}")
def evidence(evidence_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    row = db.get(Evidence, evidence_id)
    if not row: raise HTTPException(404, "Evidence not found")
    return FileResponse(row.frame_path)


@router.get("/evidence/{evidence_id}/clip")
def evidence_clip(evidence_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    row = db.get(Evidence, evidence_id)
    if not row or not row.clip_path: raise HTTPException(404, "Evidence clip not found")
    return FileResponse(row.clip_path, media_type="video/mp4")
