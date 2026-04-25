# SmritiMeds Architecture

This is how I currently think about and organize the system as the builder responsible for product direction and implementation quality.

## Top-level structure

```text
api/                     FastAPI service
web/                     React + Vite application
smritimeds/              Shared Python package
tools/scripts/           Operational utilities
research/notebooks/      Research and evaluation notebooks
docs/                    Product and architecture documents
```

Legacy aliases:

```text
backend -> api
frontend -> web
scripts -> tools/scripts
notebooks -> research/notebooks
```

## Runtime flow

### 1. Web application
- the user selects a mode and uploads an image
- `web/src/App.jsx` sends multipart form data to `POST /api/analyze`
- response is rendered into:
  - structured extraction view
  - fallback/OCR status
  - verification section
  - reminder manager

### 2. API service
- `api/main.py` receives the request
- mode routing determines whether to use:
  - OCR path (`printed_document`, `handwritten_prescription`)
  - direct Claude image analysis (`bottle_label`)
- OCR results are quality-checked
- low-quality or unavailable OCR triggers Claude image fallback
- optional local vision runs after primary analysis

### 3. Reminder generation
- analysis returns normalized JSON with schedule entries
- web layer maps schedule entries into editable reminder records
- reminders persist via browser localStorage

## Key modules

### `api/main.py`
- FastAPI routes
- health reporting
- request orchestration
- OCR-quality heuristics
- Claude fallback handling

### `smritimeds/anthropic_client.py`
- image-based Claude analysis
- text-based Claude normalization from OCR output
- response parsing and retry behavior

### `smritimeds/ocr_models.py`
- printed-document OCR adapter
- handwritten OCR adapter
- OCR route selection
- backend readiness reporting

### `smritimeds/parser.py`
- extracts JSON objects from model responses
- normalizes schedule and confidence fields

### `web/src/App.jsx`
- upload workflow
- result rendering
- fallback banners
- reminder manager with local persistence

## External dependencies

### Primary
- Anthropic API for medication extraction and normalization
- React + Vite for the web application
- FastAPI for the API service

### Optional / experimental
- `naazimsnh02/medocr-vision`
- `chinmays18/medical-prescription-ocr`
- Ultralytics YOLO
- `pillIdentifierAI/pillIdentifier`

## Failure model
My current failure strategy is intentionally conservative:
- if OCR is unavailable or returns unusable text, fall back to Claude image analysis
- if local pill-classification fails, return a warning rather than crashing the request
- if Anthropic is unavailable, return a structured error or reduced fallback analysis where possible
