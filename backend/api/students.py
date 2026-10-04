from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models import BehaviorEvent, Student

router = APIRouter(prefix="/api/students", tags=["students"])


def serialize(student):
    return {"id": student.id, "analysis_id": student.analysis_id, "track_id": student.track_id,
            "seat_id": student.seat_id, "risk_score": student.current_risk,
            "risk_level": student.risk_level, "last_seen": student.last_seen}


@router.get("")
def all_students(analysis_id: int | None = None, db: Session = Depends(get_db)):
    query = select(Student)
    if analysis_id is not None: query = query.where(Student.analysis_id == analysis_id)
    return [serialize(s) for s in db.scalars(query.order_by(Student.current_risk.desc())).all()]


@router.get("/{student_id}")
def student_detail(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if not student: raise HTTPException(404, "Student not found")
    result = serialize(student)
    events = db.scalars(select(BehaviorEvent).where(BehaviorEvent.student_id == student_id).order_by(BehaviorEvent.created_at.desc())).all()
    result["behavior_history"] = [{"behavior": e.behavior_type, "confidence": e.confidence,
                                    "video_timestamp": e.video_timestamp, "duration": e.duration} for e in events]
    return result

