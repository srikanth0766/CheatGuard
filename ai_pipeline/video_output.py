import os
import subprocess
from pathlib import Path


def make_browser_compatible(path: Path):
    converted = path.with_suffix(".browser.mp4")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(path), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-an", str(converted),
        ], check=True, capture_output=True)
        os.replace(converted, path)
    finally:
        converted.unlink(missing_ok=True)
