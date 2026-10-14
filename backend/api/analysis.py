from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal, get_db
from backend.models import Analysis

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


MODELS = {"yolo", "sav"}


def process(analysis_id: int, model: str):
    if model == "sav":
        from ai_pipeline.per_person_sav_pipeline import SavPipeline as VideoPipeline
    else:
        from ai_pipeline.pipeline import VideoPipeline
    with SessionLocal() as db:
        analysis = db.get(Analysis, analysis_id)
        if analysis: VideoPipeline().run(db, analysis)


@router.post("/start", status_code=202)
def start(analysis_id: int, tasks: BackgroundTasks, model: str = "yolo", db: Session = Depends(get_db)):
    if model not in MODELS: raise HTTPException(400, "Unknown analysis model")
    analysis = db.get(Analysis, analysis_id)
    if not analysis: raise HTTPException(404, "Analysis not found")
    if analysis.status not in {"queued", "failed"}: raise HTTPException(409, f"Analysis is {analysis.status}")
    analysis.status, analysis.error = "queued", None; db.commit()
    tasks.add_task(process, analysis_id, model)
    return {"analysis_id": analysis_id, "status": "queued", "model": model}


@router.get("/{analysis_id}")
def status(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if not analysis: raise HTTPException(404, "Analysis not found")
    return {"id": analysis.id, "status": analysis.status, "progress": analysis.progress,
            "error": analysis.error, "output_url": f"/media/{Path(analysis.output_path).name}" if analysis.output_path else None}


from pathlib import Path
