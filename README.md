# SmritiMeds

SmritiMeds is a hackathon-focused medication assistant that combines:

- **React + Vite** for a vibrant frontend
- **FastAPI** for the Python inference backend
- **Anthropic Claude Vision** for label understanding and reminder schedule generation
- **medical OCR backends** for printed and handwritten prescription extraction
- optional **YOLO pill detection**
- optional **local Hugging Face pill classification**

The name blends **Smriti** (Sanskrit for remembrance / memory) with **Meds**.

---

## Current architecture

```text
frontend/                React + Vite UI
backend/main.py          FastAPI API
anthropic_client.py      Claude Vision + OCR-text normalization
ocr_models.py            Medical OCR routing
pill_detector.py         YOLO pill detection
pill_identifier_model.py Hugging Face pill classifier integration
local_pill_pipeline.py   Hybrid local pill pipeline
```

### Frontend
- vibrant gradient UI
- upload flow for:
  - bottle / blister images
  - printed medical documents
  - handwritten prescriptions
- result panels for:
  - OCR extraction
  - structured medication schedule
  - verification summary
  - local vision beta status

### Backend routing

#### 1. Bottle / blister / pharmacy label
- primary backend: **Claude Vision**
- best for curved labels and packaging text

#### 2. Printed medical documents / forms / lab reports
- primary OCR backend: **`naazimsnh02/medocr-vision`**
- then Claude converts OCR text into reminder JSON

#### 3. Handwritten prescriptions
- primary OCR backend: **`chinmays18/medical-prescription-ocr`**
- then Claude converts OCR text into reminder JSON

#### 4. Local vision beta
- optional **YOLO** detection over pill images
- optional **`pillIdentifierAI/pillIdentifier`** candidate ranking

---

## OCR model choices

### Printed medical OCR
**Model:** `naazimsnh02/medocr-vision`

Use this for:
- printed prescriptions
- lab reports
- medical forms
- semi-structured document images

The model card describes it as a fine-tuned PaddleOCR-VL medical OCR model trained on prescriptions, lab reports, and forms.

### Handwritten prescription OCR
**Model:** `chinmays18/medical-prescription-ocr`

Use this for:
- handwritten prescriptions
- doctor notes with rough handwriting

This is a Donut-based OCR model specialized for handwritten medical prescriptions.

### Important OCR note
Both OCR models are assistive only. Their extracted text must still be reviewed by a human before clinical use.

---

## Local vision note

### YOLO detector
SmritiMeds includes a short training script for the Hugging Face dataset:
- `Ultralytics/Medical-pills`

### Hugging Face pill classifier
SmritiMeds also integrates:
- `pillIdentifierAI/pillIdentifier`

However, the currently published checkpoint appears to have **classifier metadata / weight mismatch** in the downloaded files.  
So SmritiMeds:
- downloads and caches the assets locally
- reports classifier availability clearly
- fails gracefully instead of crashing

---

## Python setup

This project is pinned to:

```bash
pyenv 3.12.10
```

Create the backend environment:

```bash
cd SmritiMeds
PYENV_VERSION=3.12.10 python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-local-vision.txt
```

### Optional OCR extras

For `medocr-vision`, install:

```bash
pip install -r requirements-ocr.txt
```

> Note: `medocr-vision` depends on `unsloth` + `trust_remote_code`. Depending on hardware and platform, this backend may not be available locally. The API surfaces that status in `/api/health`.

---

## Frontend setup

```bash
cd SmritiMeds/frontend
npm install
```

To point the frontend at a different backend:

```bash
echo 'VITE_API_BASE_URL=http://127.0.0.1:8000' > .env.local
```

---

## Run the full app

### Terminal 1 — backend
```bash
cd SmritiMeds
source .venv/bin/activate
uvicorn backend.main:app --reload
```

### Terminal 2 — frontend
```bash
cd SmritiMeds/frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

---

## Downloaded local assets

Current local assets used by the project:

- YOLO base weights:
  - `models/yolo11n.pt`
- Hugging Face pill model snapshot:
  - `models/pillIdentifierAI-pillIdentifier/`
- pill label encoder:
  - `.cache/pill_identifier/encoder.npy`
- Ultralytics medical pills dataset:
  - `data/Ultralytics-Medical-pills/`

### Included sample images

Two ready-to-test sample images are now available under:

- `sample_images/sample_prescription_medocr.png`
- `sample_images/sample_lab_report_medocr.png`

Reference OCR text is stored beside them:

- `sample_images/sample_prescription_medocr.txt`
- `sample_images/sample_lab_report_medocr.txt`

---

## Train the YOLO pill detector

```bash
cd SmritiMeds
source .venv/bin/activate
python scripts/train_yolo_medical_pills.py --epochs 5 --imgsz 416 --device cpu
```

This writes weights under:

```text
models/medical-pills-yolo/weights/best.pt
```

Then run with:

```bash
export SMRITIMEDS_YOLO_WEIGHTS=models/medical-pills-yolo/weights/best.pt
```

---

## API endpoints

### `GET /api/health`
Returns:
- Anthropic configured or not
- OCR backend availability
- local vision cache status

### `POST /api/analyze`
Multipart form fields:
- `mode`
  - `auto`
  - `bottle_label`
  - `printed_document`
  - `handwritten_prescription`
- `run_local_vision`
  - `true` / `false`
- `label_image`
  - required
- `verification_image`
  - optional

---

## What the app currently does

- reads bottle / blister / document images
- routes printed medical docs to `medocr-vision`
- routes handwritten prescriptions to Donut OCR
- uses Claude to convert OCR text or visual label content into structured reminder JSON
- optionally runs local pill detection / classification beta
- renders results in a polished React frontend

---

## Safety boundaries

SmritiMeds is a hackathon prototype. It does **not**:

- provide medical diagnosis
- prescribe treatment
- replace pharmacists or clinicians
- guarantee pill identity
- guarantee OCR accuracy

Always require human review for extracted medical information.
