from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api import alerts, analysis, students, videos
from backend.core.config import settings
from backend.core.database import Base, engine
import backend.models

Base.metadata.create_all(engine)
settings.upload_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="CheatGuard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(videos.router)
app.include_router(analysis.router)
app.include_router(students.router)
app.include_router(alerts.router)
app.mount("/media", StaticFiles(directory=settings.upload_dir), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok", "models": {
        "yolo": {"path": str(settings.model_path), "exists": settings.model_path.exists()},
        "sav": {"path": str(settings.sav_model_path), "exists": settings.sav_model_path.exists()},
    }}
