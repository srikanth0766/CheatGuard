from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal, get_db
from backend.models import Analysis

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def process(analysis_id: int):
    from ai_pipeline.per_person_sav_pipeline import SavPipeline as VideoPipeline
    with SessionLocal() as db:
        analysis = db.get(Analysis, analysis_id)
        if analysis: VideoPipeline().run(db, analysis)


@router.post("/start", status_code=202)
def start(analysis_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis: raise HTTPException(404, "Analysis not found")
    if analysis.status not in {"queued", "failed"}: raise HTTPException(409, f"Analysis is {analysis.status}")
    analysis.status, analysis.error = "queued", None; db.commit()
    tasks.add_task(process, analysis_id)
    return {"analysis_id": analysis_id, "status": "queued", "model": "sav-yolo"}


@router.post("/{analysis_id}/stop")
def stop(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis: raise HTTPException(404, "Analysis not found")
    if analysis.status not in {"queued", "running"}: raise HTTPException(409, f"Analysis is {analysis.status}")
    analysis.status, analysis.error = "cancelled", None
    db.commit()
    return {"analysis_id": analysis_id, "status": "cancelled"}


@router.get("/{analysis_id}")
def status(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis: raise HTTPException(404, "Analysis not found")
    return {"id": analysis.id, "status": analysis.status, "progress": analysis.progress,
            "error": analysis.error, "output_url": f"/media/{Path(analysis.output_path).name}" if analysis.output_path else None}


from pathlib import Path
