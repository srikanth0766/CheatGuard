FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY ai_pipeline ai_pipeline
RUN mkdir -p uploads/videos evidence/frames evidence/clips
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
