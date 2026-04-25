<h1 align="center">SmritiMeds</h1>

<p align="center">
  <img src="data/icon.png" alt="SmritiMeds icon" width="120" />
</p>

<p align="center">
  <img src="demo/SmritiMeds_Demo.gif" alt="SmritiMeds demo" width="700" />
</p>

I’m building SmritiMeds as a product I would want to trust for medication understanding and reminder management:

- extracting medication instructions from labels and medical documents
- converting those instructions into editable reminders
- reviewing OCR confidence and fallback behavior
- optionally running local pill detection and classification experiments

I chose the name because it blends **Smriti** (Sanskrit for remembrance / memory) with **Meds** — the product is about helping people remember, verify, and manage medication information with more confidence.

---

## Product overview

This README is written from my perspective as the builder of the project.

### Core capabilities
- **Medication instruction extraction**
  - bottle labels
  - blister packs
  - printed medical documents
  - handwritten prescriptions
- **Reminder management**
  - import suggested reminders from analysis
  - edit title, medication, dose, time, and notes
  - pause, complete, delete, and manually add reminders
  - persist reminders locally in the web application
- **Confidence-aware workflows**
  - OCR service status visibility
  - automatic Claude fallback when OCR is unavailable or low quality
  - manual review warnings for uncertain output

### Supported analysis paths
1. **Bottle / blister / pharmacy label**
   - Claude Vision-first
2. **Printed medical documents**
   - `naazimsnh02/medocr-vision`, with Claude fallback
3. **Handwritten prescriptions**
   - `chinmays18/medical-prescription-ocr`, with Claude fallback
4. **Optional local vision**
   - YOLO pill detection
   - `pillIdentifierAI/pillIdentifier` candidate ranking

---

## System architecture

```text
web/                     React + Vite application
api/main.py              FastAPI API service
smritimeds/              Shared Python package
docs/                    Product and architecture documentation
tools/scripts/           Operational utilities
research/notebooks/      Research and evaluation notebooks
```

### Web application
- responsive React UI
- upload and routing controls
- structured results and fallback banners
- reminder manager with local persistence

### API service
- FastAPI endpoints for health and analysis
- OCR model routing
- Claude-based extraction normalization
- optional local vision enrichment

---

## Environment setup

### Python

Pinned version:

```bash
pyenv 3.12.10
```

Create the environment:

```bash
cd SmritiMeds
PYENV_VERSION=3.12.10 python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-local-vision.txt
```

Optional OCR extras for `medocr-vision`:

```bash
pip install -r requirements-ocr.txt
```

Install SmritiMeds as a local package:

```bash
pip install -e .
```

Add configuration:

```bash
cp .env.example .env
```

Expected key:

```text
ANTHROPIC_API_KEY
```

### Web application

```bash
cd SmritiMeds/web
npm install
```

Optional web application API override:

```bash
echo 'VITE_API_BASE_URL=http://127.0.0.1:8000' > .env.local
```

---

## Running the application

### Terminal 1 — API service
```bash
cd SmritiMeds
source .venv/bin/activate
uvicorn api.main:app --reload
```

### Terminal 2 — web application
```bash
cd SmritiMeds/web
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Backend health:

```text
http://127.0.0.1:8000/api/health
```

---

## Primary workflows

### 1. Analyze a medication source
- choose a mode:
  - `Auto Route`
  - `Bottle / Blister`
  - `Printed Medical Doc`
  - `Handwritten Rx`
- upload a primary image
- optionally upload a pill verification image
- run analysis

### 2. Review the extracted result
- medication name
- strength
- instructions
- suggested schedule
- confidence notes
- OCR fallback status

### 3. Manage reminders
- imported reminders appear in **Reminder manager**
- edit:
  - reminder title
  - medication
  - dose
  - time of day
  - reminder time
  - notes
- change state:
  - active / paused
  - completed
- add manual reminders
- delete reminders
- clear completed reminders

---

## Local assets

These are the local assets I currently keep in the project:

- YOLO base weights:
  - `models/yolo11n.pt`
- Hugging Face pill model snapshot:
  - `models/pillIdentifierAI-pillIdentifier/`
- pill label encoder:
  - `.cache/pill_identifier/encoder.npy`
- Ultralytics medical pills dataset:
  - `data/Ultralytics-Medical-pills/`

### Included sample images

Ready-to-test examples:

- `sample_images/sample_prescription_medocr.png`
- `sample_images/sample_lab_report_medocr.png`

Reference OCR text:

- `sample_images/sample_prescription_medocr.txt`
- `sample_images/sample_lab_report_medocr.txt`

### Research notebooks

Canonical notebook location:

- `research/notebooks/01_claude_vision_smoke_test.ipynb`
- `research/notebooks/02_prompt_eval_and_schedule_render.ipynb`

---

## OCR and local vision notes

### Printed medical OCR
Model:
- `naazimsnh02/medocr-vision`

Best for:
- printed prescriptions
- lab reports
- medical forms

### Handwritten prescription OCR
Model:
- `chinmays18/medical-prescription-ocr`

Best for:
- handwritten prescriptions
- doctor notes with rough handwriting

### Local pill classifier note
Model:
- `pillIdentifierAI/pillIdentifier`

Current caveat:
- the published checkpoint appears to have classifier metadata / weight mismatch
- SmritiMeds caches the assets locally and fails gracefully when loading is unreliable

### Visual-only authentication boundary

SmritiMeds applies an explicit **visual-only confidence penalty** to the local vision path.

Why:
- local camera analysis can assess surface structure, color, shape, and imprint cues
- it cannot confirm chemical authenticity
- visually convincing counterfeits can still pass a surface-only check

The local vision UI now surfaces:
- a visual-only confidence penalty
- an adjusted visual confidence value
- a structural-surface-only disclaimer
- risk factors explaining why the result should not be treated as chemical authentication

### YOLO training

```bash
cd SmritiMeds
source .venv/bin/activate
python tools/scripts/train_yolo_medical_pills.py --epochs 5 --imgsz 416 --device cpu
```

Trained weights output:

```text
models/medical-pills-yolo/weights/best.pt
```

Set runtime path:

```bash
export SMRITIMEDS_YOLO_WEIGHTS=models/medical-pills-yolo/weights/best.pt
```

---

## API reference

### `GET /api/health`
Returns:
- Anthropic configuration state
- OCR backend availability
- local vision cache state

### `POST /api/analyze`
Multipart fields:
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

## Current product boundaries

SmritiMeds is an assistive medication workflow application. It does **not**:

- provide medical diagnosis
- prescribe treatment
- replace pharmacists or clinicians
- guarantee pill identity
- guarantee OCR accuracy

Human review is still required for extracted medical information and reminder interpretation.

---

## Documentation

- Product requirements: `docs/PRODUCT_REQUIREMENTS.md`
- System architecture: `docs/ARCHITECTURE.md`
- PillSure safety note: `docs/PILLSURE_NOTE.md`
- LinkedIn post draft: `docs/LINKEDIN_POST.md`

Compatibility note:
- `backend/` and `frontend/` remain available as aliases to the canonical `api/` and `web/` directories.
- root-level `PRODUCT_REQUIREMENTS.md` and `ARCHITECTURE.md` are lightweight pointers to the canonical docs in `docs/`.
- `scripts/` and `notebooks/` remain available as aliases to the canonical `tools/scripts/` and `research/notebooks/` locations.
