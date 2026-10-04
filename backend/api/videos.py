from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from backend.core.config import settings
from backend.core.database import get_db
from backend.models import Analysis

router = APIRouter(prefix="/api/videos", tags=["videos"])
ALLOWED = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


@router.post("", status_code=201)
def upload_video(video: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in ALLOWED: raise HTTPException(400, "Unsupported video type")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    path = settings.upload_dir / f"{uuid4().hex}{suffix}"
    with path.open("wb") as output:
        while chunk := video.file.read(1024 * 1024): output.write(chunk)
    analysis = Analysis(video_path=str(path))
    db.add(analysis); db.commit(); db.refresh(analysis)
    return {"analysis_id": analysis.id, "filename": video.filename, "status": analysis.status}

