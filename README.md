# CheatGuard

CheatGuard is an examination-video analysis system that detects and tracks students, classifies their behavior, applies temporal malpractice rules, assigns per-student risk, and stores evidence for review. It consists of a React dashboard, a FastAPI backend, an AI video-processing pipeline, and SQLite or PostgreSQL persistence.

The application supports two selectable analysis modes:

1. **YOLO26 Large** — direct object/behavior detection with ByteTrack identities.
2. **SAV MobileNet** — YOLO/ByteTrack person localization followed by per-person SAV behavior classification and rule-based malpractice decisions.

The live-camera workflow was intentionally removed. The current application analyzes uploaded video files only.

## Project objectives

- Upload recorded examination-hall footage from a browser.
- Choose the AI model used for analysis.
- Detect and track multiple students throughout the video.
- Keep a stable track ID for each detected student where ByteTrack can maintain identity.
- Classify student behavior and suppress isolated, single-frame predictions.
- Distinguish normal activity from configured malpractice behavior.
- Maintain per-student suspicion state across time.
- Save an evidence frame and short preceding clip when an alert is produced.
- Return a browser-playable annotated video.
- Display processing progress, tracked students, risk state, alerts, and evidence in the dashboard.

## System architecture

```text
React dashboard
    |
    | upload video + selected model
    v
FastAPI application
    |
    +-- video storage
    +-- background analysis task
    +-- SQLite/PostgreSQL records
    |
    +---------------------------+
    |                           |
    v                           v
YOLO pipeline              SAV pipeline
YOLO26 detections          YOLO26 person boxes
ByteTrack IDs              ByteTrack IDs
Temporal rules             Per-person SAV crops
Risk scoring               SAV temporal rules
    |                           |
    +-------------+-------------+
                  v
       annotated H.264 video
       alerts + frame/clip evidence
```

The frontend polls analysis and student endpoints every two seconds while a job is active. It also refreshes the global alert history every two seconds.

## Models and supplied assets

### YOLO26 model

- Checkpoint: `../best_large.pt`
- Runtime: Ultralytics YOLO
- Tracking: ByteTrack through `model.track(..., persist=True, tracker="bytetrack.yaml")`
- Default detection confidence: `0.25`
- Dataset: `../classroom.v1i.yolo26 /`
- Dataset size: 1,305 training images, 327 validation images, and 163 test images
- Dataset license: CC BY 4.0

The dataset export contains numeric names, so the application maps IDs in the following assumed order:

| ID | YOLO behavior |
|---:|---|
| 0 | normal |
| 1 | looking around |
| 2 | suspicious interaction |
| 3 | mobile phone |
| 4 | hands under desk |
| 5 | passing items |
| 6 | whispering |

This order must be verified against the original Roboflow project before the output is treated as production evidence. It can be overridden with the `CLASS_NAMES` environment setting.

### SAV model

- Checkpoint: `../sav_training/mini100/best_100.pt`
- Architecture: MobileNet V3 Small with a 15-output classifier head
- Task: multi-label classroom-action classification
- Activation: sigmoid per class
- Runtime threshold used by rules: `0.5`
- Training loss: binary cross-entropy with logits
- Training optimizer: AdamW

The checkpoint was trained on 100 SAV clips: 80 training clips and 20 validation clips, producing 7,200 training frames and 1,800 validation frames. The stored best checkpoint came from epoch 18.

Reported validation results for that checkpoint:

| Metric | Result |
|---|---:|
| Micro F1 | 0.7866 |
| Macro F1 | 0.5521 |
| Label accuracy | 0.7770 |
| Exact multi-label match | 0.0461 |

The SAV checkpoint was trained from whole video frames with clip-level multi-label annotations. It was not trained with person-level crop annotations. CheatGuard now applies it to tracked student crops so actions can be associated with an ID, but this introduces a training/inference distribution difference. Reliable deployment requires evaluation and preferably retraining or fine-tuning on person crops from actual examination footage.

### SAV annotation conversion and YOLO26 experiment

The SAV data was evaluated through two training approaches:

1. **Native SAV approach.** The original SAV annotations and class structure were retained, and a multi-label classifier was trained to recognize the 15 classroom actions.
2. **YOLO26 approach.** The SAV annotations were converted into YOLO-format detection annotations and used to train a YOLO26 model. Each annotated bounding box was converted to YOLO's normalized `class_id x_center y_center width height` representation, and the SAV action IDs were mapped to the corresponding YOLO class IDs.

This conversion allowed the second experiment to learn localization and action labels in a single detection model. It also made the results directly compatible with ByteTrack, because YOLO supplies a bounding box and confidence for every detection before the tracker assigns a persistent student ID.

The project comparison found that the native SAV approach and the SAV-to-YOLO26 approach produced approximately similar action-recognition performance on the available evaluation footage. The practical difference was processing throughput: **YOLO26 processed video faster** and integrated more naturally with per-person detection and ByteTrack. For that reason, YOLO26 is the stronger option when analysis speed and an end-to-end detection/tracking workflow are the main requirements. The native SAV path remains in the application for model comparison and experimentation.

No separate raw timing table for this comparison is stored in the repository, so the conclusion is intentionally reported qualitatively rather than as an unsupported FPS or latency number.

## SAV's 15 classes and current policy

The model always produces a probability for all 15 classes. The policy layer decides which results affect malpractice state.

| ID | SAV class | Current treatment |
|---:|---|---|
| 1 | `sit` | Normal |
| 2 | `stand` | Ignored |
| 3 | `look_forward` | Normal |
| 4 | `look_sideways` | Malpractice candidate |
| 5 | `read` | Ignored |
| 6 | `flip_books` | Ignored |
| 7 | `touch_sth` | Ignored |
| 8 | `raise_hand` | Ignored |
| 9 | `hands_down` | Ignored |
| 10 | `take_notes` | Normal |
| 11 | `applaud` | Ignored |
| 12 | `bend` | Malpractice candidate |
| 13 | `turn_around` | Ignored because no policy was assigned |
| 14 | `talk_with_others` | Critical malpractice candidate |
| 15 | `answer_questions` | Ignored |

`stand` was initially treated as non-normal but produced too many false flags, so it was removed from malpractice scoring and is now ignored.

Ignored classes neither create events nor directly increase suspicion. Normal observations allow accumulated suspicion to decay.

## SAV per-person pipeline

The SAV path is implemented in `ai_pipeline/per_person_sav_pipeline.py`:

1. Open the uploaded video with OpenCV.
2. Read its FPS, frame count, width, and height.
3. Run the existing YOLO detector on every frame.
4. Use persistent ByteTrack IDs to associate detections across frames.
5. Clamp every bounding box to valid image coordinates.
6. Create one database `Student` record per new track ID.
7. Twice per second, crop every active tracked student from the frame.
8. Resize and normalize the crop with the standard MobileNet V3 preprocessing transform.
9. Run SAV and calculate sigmoid probabilities for all 15 labels.
10. Pass the predictions to the per-track temporal rule engine.
11. Update internal suspicion, risk level, behavior events, alerts, and evidence.
12. Assign approximate classroom seats based on the spatial order of active boxes.
13. Draw the track ID, behavior state, and risk-colored box on the output frame.
14. Write the annotated frames to an intermediate MP4.
15. Convert the result to H.264/yuv420p with FFmpeg for reliable browser playback.

The SAV classifier is sampled at approximately two times per second (`fps / 2`). YOLO and ByteTrack still process every video frame so identity and boxes remain continuous.

## SAV temporal malpractice rules

Predictions are stored independently for each ByteTrack ID. A class must repeat inside a short rolling window before it becomes confirmed malpractice:

| Class | Confirmation rule | Internal suspicion increase | Critical |
|---|---:|---:|---|
| `look_sideways` | 3 of the last 4 SAV samples | `15 × confidence` | No |
| `bend` | 3 of the last 4 SAV samples | `20 × confidence` | No |
| `talk_with_others` | 2 of the last 3 SAV samples | `35 × confidence` | Yes |

This temporal confirmation prevents a single noisy prediction from immediately becoming an incident.

The internal suspicion value is capped at 100 but is not displayed as a numeric score in the SAV student panel or SAV video overlay. It remains an implementation detail used to decide when non-critical evidence should be stored.

- Default evidence threshold: `51`
- Clean-sample decay: `10` points per SAV sampling interval
- Critical behavior: evidence is created immediately after temporal confirmation, even below the threshold
- Non-critical behavior: evidence is created only after the internal suspicion reaches the threshold
- Alert cooldown: five seconds per `(track ID, behavior)` pair

When a student produces normal observations such as sitting, looking forward, or taking notes, their suspicion decreases toward zero. A clean period therefore recovers from earlier suspicious behavior instead of leaving the student permanently high-risk.

## YOLO analysis pipeline

The YOLO path is implemented in `ai_pipeline/pipeline.py` and remains separate from the SAV policy.

For each frame it:

1. Runs YOLO detection and ByteTrack.
2. Creates or updates a `StudentState` for each track ID.
3. Applies temporal confirmation to selected YOLO behavior labels.
4. Optionally runs RTMPose on the detected crop when MMPose is installed.
5. Creates a database student record for new tracks.
6. Applies cumulative weighted risk scoring for non-normal behavior.
7. Stores behavior and risk history.
8. Assigns seats and nearest-neighbor IDs.
9. Draws the ID, behavior, and risk score on the frame.
10. Creates evidence when the alert threshold is reached.

YOLO risk weights are:

| Behavior | Base weight |
|---|---:|
| normal | 0 |
| looking around | 10 |
| suspicious interaction | 15 |
| whispering | 15 |
| hands under desk | 20 |
| mobile phone | 30 |
| passing items | 30 |

The YOLO scorer also applies bounded frequency and duration factors. Risk levels are low at 0–20, medium above 20–50, high above 50–75, and critical above 75.

## Evidence generation

An alert contains:

- Student database ID
- Internal risk/suspicion value at the time of the alert
- Human-readable reason
- Timestamp within the source video
- Alert status
- JPEG evidence frame
- Short MP4 evidence clip containing buffered frames immediately before the incident and the current frame

Evidence frames are written to `evidence/frames/`, and clips are written to `evidence/clips/`. The alert panel shows the latest alerts first and provides direct links to both artifacts.

For SAV, critical `talk_with_others` events use the reason `Critical malpractice: talk with others`. Other SAV alerts use the normal threshold-based reason. The annotated full output video is stored under `uploads/videos/`.

## Browser-compatible video output

OpenCV writes the initial output with the `mp4v` codec. Many browsers cannot play that codec reliably. After analysis finishes, `ai_pipeline/video_output.py` calls FFmpeg to convert the video to:

- H.264 (`libx264`)
- `yuv420p` pixel format
- fast-start MP4 layout
- no audio track

The converted file replaces the intermediate output. Docker installs FFmpeg explicitly for this step.

## Dashboard workflow

The React dashboard provides:

- A dropdown with `YOLO26 Large` and `SAV MobileNet`
- Video-file upload
- Disabled upload/model controls while analysis is running
- Processing status and percentage
- Browser playback of the analyzed video
- Per-analysis tracked student list
- Risk-level indicator
- Global alert history with evidence thumbnails, frames, and clips

For SAV, the numeric 0–100 value is hidden in the student panel and output overlay. The qualitative risk state and evidence system remain available. YOLO continues to show its numeric risk score.

The browser sends the selected model to:

```text
POST /api/analysis/start?analysis_id=<id>&model=yolo
POST /api/analysis/start?analysis_id=<id>&model=sav
```

Local development uses a Vite proxy for `/api` and `/media`, avoiding browser CORS and localhost address issues. Docker supplies an explicit `VITE_API_URL`.

## Backend and database

FastAPI starts the configured database, creates missing SQLAlchemy tables, registers API routes, and serves analyzed videos under `/media`.

The main records are:

- `Analysis`: input path, output path, status, progress, error, creation time
- `Student`: analysis ID, ByteTrack ID, seat, current internal risk, risk level, last seen time
- `BehaviorEvent`: student, behavior, confidence, video timestamp, duration
- `RiskScore`: student, numeric internal score, risk level, creation time
- `Alert`: student, internal score, reason, video timestamp, status, creation time
- `Evidence`: alert, frame path, optional clip path, creation time

SQLite is the zero-configuration local default. Docker Compose uses PostgreSQL 16.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check API and both checkpoint paths |
| `POST` | `/api/videos` | Upload an allowed video and create an analysis |
| `POST` | `/api/analysis/start?analysis_id=ID&model=yolo|sav` | Start background processing |
| `GET` | `/api/analysis/{id}` | Read status, progress, errors, and output URL |
| `GET` | `/api/students?analysis_id=ID` | List students for an analysis |
| `GET` | `/api/students/{id}` | Read one student and behavior history |
| `GET` | `/api/alerts` | List all alerts, newest first |
| `GET` | `/api/alerts/{id}` | Read one alert |
| `GET` | `/api/evidence/{id}` | Download/view an evidence frame |
| `GET` | `/api/evidence/{id}/clip` | Download/view an evidence clip |
| `GET` | `/media/{filename}` | Stream an analyzed video |

Accepted upload extensions are `.mp4`, `.avi`, `.mov`, `.mkv`, and `.webm`. Unsupported extensions return HTTP 400. Starting an unknown model returns HTTP 400; missing analyses return HTTP 404; starting an already-running or completed analysis returns HTTP 409.

Interactive API documentation is available at `/docs` while the backend runs.

## Configuration

Configuration is loaded from environment variables or `cheatguard/.env`.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///.../cheatguard.db` | SQLAlchemy database connection |
| `MODEL_PATH` | `../best_large.pt` | YOLO checkpoint |
| `SAV_MODEL_PATH` | `../sav_training/mini100/best_100.pt` | SAV checkpoint |
| `UPLOAD_DIR` | `uploads/videos` | Uploaded and analyzed videos |
| `EVIDENCE_DIR` | `evidence` | Evidence frames and clips |
| `ALERT_THRESHOLD` | `51` | Non-critical evidence threshold |
| `DETECTION_CONFIDENCE` | `0.25` | YOLO detection threshold |
| `CLASS_NAMES` | Seven comma-separated YOLO labels | YOLO class mapping |

## Run locally

Requirements:

- Python 3.11 recommended
- Node.js 20 or newer
- FFmpeg available on `PATH`
- Both model checkpoint files at the paths listed above

Install dependencies from the `cheatguard` directory:

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cd frontend
npm install
```

Run the backend from `cheatguard/`:

```bash
.venv/bin/uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open:

- Dashboard: `http://localhost:5173`
- API documentation: `http://localhost:8000/docs`

## Run with Docker

From the `cheatguard` directory:

```bash
docker compose up --build
```

Open:

- Dashboard: `http://localhost:5174`
- API documentation: `http://localhost:8001/docs`

Docker Compose starts PostgreSQL, the API, and the Vite frontend. It mounts both checkpoints read-only and persists uploads, evidence, and PostgreSQL data. Override ports with `API_PORT` and `FRONTEND_PORT` if necessary.

## Testing and evaluation

Run automated tests:

```bash
.venv/bin/pytest -q
```

The tests cover:

- YOLO temporal behavior confirmation
- Weighted and capped YOLO risk scoring
- Alert cooldown behavior
- SAV normal-action handling
- SAV ignored classes, including `stand`
- Per-student SAV temporal confirmation
- Critical `talk_with_others` classification

Build the frontend:

```bash
cd frontend
npm run build
```

Evaluate YOLO on the supplied test split:

```bash
.venv/bin/python scripts/evaluate_model.py
```

Recorded YOLO results on the 163-image test split:

| Metric | Result |
|---|---:|
| Precision | 0.959 |
| Recall | 0.889 |
| mAP50 | 0.933 |
| mAP50-95 | 0.753 |

Class 6 has no examples in the test split and therefore cannot receive a held-out per-class score.

### Native SAV versus SAV-to-YOLO26 conclusion

The two SAV experiments reached broadly similar detection/classification performance in the project evaluation. YOLO26 had the higher processing speed and required a simpler runtime path for localization, tracking, and annotation. The final engineering conclusion was therefore:

- Use **YOLO26** when throughput, direct person localization, and ByteTrack integration are priorities.
- Retain the **native SAV model** as an alternative experimental classifier and for comparison with the converted YOLO26 training approach.
- Do not claim a precise speedup until both models are benchmarked on the same hardware, input resolution, videos, and confidence thresholds.

## Important limitations

1. **SAV is not a person detector.** Person boxes and ByteTrack IDs in SAV mode come from the YOLO checkpoint.
2. **SAV was trained on whole frames.** Applying it to person crops enables per-ID decisions but may produce false positives because crop-level input differs from its training data.
3. **Detection cannot guarantee every person.** Occlusion, small subjects, image quality, camera angle, lighting, confidence thresholds, and detector training data can all cause missed or fragmented tracks.
4. **Track IDs can switch.** ByteTrack improves continuity but cannot guarantee identity across long occlusions or scene cuts.
5. **Rules are policy, not ground truth.** The normal, ignored, malpractice, temporal, critical, increment, decay, and threshold values are manually configured decisions and require validation with exam administrators.
6. **SAV ignored classes are intentionally discarded.** They do not create behavior events even when their model confidence is high.
7. **Alert history is global.** The current dashboard displays alerts across analyses rather than filtering them to only the active upload.
8. **Background tasks are in-process.** A server restart can interrupt an active analysis; a production deployment should use a durable job queue.
9. **No authentication is implemented.** The current dashboard and API are suitable for controlled development environments, not public deployment.
10. **Privacy and compliance require separate work.** Examination footage and evidence contain sensitive personal data and need retention policies, authorization, access controls, encryption, and applicable consent/legal review.
11. **Automated output needs human review.** Alerts should be treated as review candidates, never as conclusive proof of malpractice.

## Recommended future work

- Retrain SAV on person-level crops with per-person action labels.
- Add a dedicated person detector rather than relying on behavior-class detections for SAV localization.
- Calibrate class thresholds separately instead of using `0.5` for every SAV class.
- Evaluate precision, recall, false-alert rate, identity switches, and missed-student rate on unseen examination videos.
- Add analysis-specific alert filtering.
- Add authentication, roles, audit logs, retention controls, and encryption.
- Move background analysis to Celery, RQ, or another durable worker system.
- Batch SAV crop inference for better GPU utilization.
- Convert evidence clips to H.264 as well as full output videos.
- Add downloadable analysis reports and summary statistics.

## Key source files

| File | Responsibility |
|---|---|
| `frontend/src/App.jsx` | Upload workflow, model selection request, polling |
| `frontend/src/components/VideoMonitor.jsx` | Model dropdown, video upload, progress, playback |
| `frontend/src/components/StudentPanel.jsx` | Tracked-student status |
| `frontend/src/components/AlertPanel.jsx` | Alert and evidence display |
| `backend/main.py` | FastAPI application and routes |
| `backend/api/videos.py` | Video validation and storage |
| `backend/api/analysis.py` | Model dispatch and job status |
| `backend/api/students.py` | Student and behavior-history endpoints |
| `backend/api/alerts.py` | Alert and evidence endpoints |
| `backend/models/entities.py` | SQLAlchemy data model |
| `ai_pipeline/pipeline.py` | YOLO video pipeline |
| `ai_pipeline/per_person_sav_pipeline.py` | Per-person SAV pipeline |
| `ai_pipeline/behavior/sav_behavior_analyzer.py` | SAV class policy and temporal rules |
| `ai_pipeline/detection/student_detector.py` | YOLO and ByteTrack adapter |
| `ai_pipeline/risk/risk_scorer.py` | YOLO risk scoring |
| `ai_pipeline/alerts/alert_manager.py` | Alert cooldown and evidence creation |
| `ai_pipeline/video_output.py` | Browser-compatible H.264 conversion |
| `tests/test_sav_behavior.py` | SAV policy tests |

## Responsible-use note

CheatGuard is a decision-support prototype. Model predictions can be wrong, biased, or incomplete. A recorded alert should initiate human review of the surrounding context; it should not automatically determine guilt or disciplinary action.
