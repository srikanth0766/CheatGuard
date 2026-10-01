from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{ROOT / 'cheatguard.db'}"
    model_path: Path = ROOT.parent / "best_large.pt"
    sav_model_path: Path = ROOT.parent / "sav_training/mini100/best_100.pt"
    upload_dir: Path = ROOT / "uploads/videos"
    evidence_dir: Path = ROOT / "evidence"
    alert_threshold: float = 51
    detection_confidence: float = 0.25
    class_names: str = (
        "normal,looking_around,suspicious_interaction,mobile_phone,"
        "hands_under_desk,passing_items,whispering"
    )
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    @property
    def labels(self) -> dict[int, str]:
        return dict(enumerate(x.strip() for x in self.class_names.split(",")))


settings = Settings()
