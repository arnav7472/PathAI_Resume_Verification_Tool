# PathAI Verify

AI-powered resume verification and fraud-detection platform with OCR-enhanced document analysis.

Live site: https://path-ai-e215.onrender.com

![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-646CFF)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![OCR](https://img.shields.io/badge/OCR-Tesseract%20%2B%20OpenCV-blue)
![Deployment](https://img.shields.io/badge/deploy-Vercel%20%2B%20Docker-black)

## Overview

PathAI Verify helps recruiters, hiring teams, and technical screeners evaluate whether a resume is internally consistent and aligned with a job description. Resume inflation is hard to catch manually: skill lists may not be supported by project or experience bullets, seniority claims can be vague, and scanned resumes often fail standard text extraction.

The platform combines document parsing, OCR fallback, structured resume section analysis, job-description matching, and explainable scoring. It extracts candidate claims, maps evidence snippets back to resume sections, flags weak or missing support, and presents results in a recruiter-friendly dashboard.

PathAI Verify currently focuses on:

- PDF and DOCX resume ingestion
- OCR fallback for scanned PDFs
- Resume section parsing and normalization
- Skill and action-verb extraction
- Job-description compatibility scoring
- Evidence-backed claim verification
- Risk, confidence, and verdict generation
- Timeline and employment-span consistency checks
- Dashboard, reports, evidence, skills, and settings views

## Features

- **Secure upload flow**: Validates file type, file signature, empty uploads, and a 10 MB upload limit before parsing.
- **PDF and DOCX support**: Uses PyMuPDF for PDF text extraction and `python-docx` for DOCX paragraphs and tables.
- **OCR fallback**: Automatically runs Tesseract OCR when a PDF has too little extractable embedded text.
- **Image preprocessing**: Converts rendered PDF pages to grayscale and applies Otsu thresholding with OpenCV before OCR.
- **Resume parsing**: Normalizes text, detects resume sections, and splits content into sentence-level evidence units.
- **Skill extraction**: Uses a curated skill alias vocabulary covering software, cloud, DevOps, security, AI/ML, and API terms.
- **Job-description matching**: Extracts required skills, domains, certifications, and action verbs from the job description.
- **Verification scoring**: Computes compatibility, risk, confidence, weak areas, missing skills, and final verdicts.
- **Fraud and inconsistency detection**: Flags unsupported skills, buzzword-heavy claims, weak evidence, missing JD requirements, timeline gaps, overlaps, and unusually long spans.
- **ATS-friendly processing**: Works from normalized text and structured resume sections rather than visual layout assumptions.
- **Results dashboard**: Shows summary metrics, findings, matched/missing skills, claim evidence, timeline analysis, and report history.
- **Configurable strictness**: Supports low, medium, and high verification strictness plus a cross-reference toggle.

## Tech Stack

### Frontend

| Area | Technology |
| --- | --- |
| App framework | React 18, Vite 6 |
| Language | TypeScript |
| Routing | React Router 7 |
| Styling | Tailwind CSS 4, custom PathAI theme tokens |
| UI primitives | Radix UI components |
| Icons | Lucide React, MUI icons |
| Charts/visualization | Recharts |
| Notifications | Sonner |
| Animation | Motion |
| State persistence | React context, browser `localStorage` |

### Backend

| Area | Technology |
| --- | --- |
| API framework | FastAPI |
| Server | Uvicorn |
| Request validation | Pydantic |
| CORS | FastAPI CORSMiddleware |
| File upload parsing | `python-multipart`, Starlette upload handling |
| Runtime | Python 3.11 in Docker |

### AI / OCR / Analysis

| Area | Technology |
| --- | --- |
| PDF text extraction | PyMuPDF |
| DOCX extraction | python-docx |
| OCR engine | Tesseract via pytesseract |
| Image preprocessing | Pillow, OpenCV headless, NumPy |
| Resume intelligence | Deterministic NLP-style heuristics, curated skill aliases, section-aware evidence scoring |
| Verification logic | Compatibility scoring, confidence bands, timeline analysis, consistency signals |

### Database

| Area | Current implementation |
| --- | --- |
| Persistent backend database | Not currently configured |
| Scan history | Stored client-side in `localStorage` |
| Authentication/session storage | Not currently implemented |

### Deployment

| Area | Technology |
| --- | --- |
| Static frontend | Vercel configuration for Vite |
| Full-stack container | Docker multi-stage build |
| Backend hosting config | Railway start command |
| Production static serving | FastAPI serves `dist/` when present |

### Dev Tools

| Area | Technology |
| --- | --- |
| Frontend package manager | npm with `package-lock.json` |
| Design prototype package manager | pnpm lockfile in `pathai_design/` |
| Build scripts | `npm run build`, `npm run dev`, `npm start` |
| Python dependencies | `requirements.txt` |

## Architecture

```text
Candidate upload / pasted text
        |
        v
React + Vite dashboard
        |
        | POST /extract-text
        v
FastAPI upload validation
        |
        +--> PDF: PyMuPDF text extraction
        |       |
        |       +--> OCR fallback: render PDF page -> OpenCV preprocessing -> Tesseract
        |
        +--> DOCX: python-docx paragraph/table extraction
        |
        v
Normalized resume text
        |
        | POST /verify
        v
Section parser -> skill discovery -> JD extraction -> evidence extractor
        |
        v
Verification engine
        |
        +--> compatibility score
        +--> risk score
        +--> confidence score
        +--> claims and evidence snippets
        +--> timeline analysis
        |
        v
Summary, Skills, Evidence, Reports, and Settings dashboards
```

The backend intentionally returns explainable evidence objects rather than a black-box-only score. Each claim can include evidence level, confidence, section label, snippet text, evidence type, and warning text.

## Folder Structure

```text
Path-ai/
|-- backend/
|   |-- main.py                     # FastAPI app, upload validation, API routes, SPA serving
|   |-- analysis_engine.py          # Public analysis facade
|   |-- parser/                     # PDF, DOCX, OCR, and legacy resume parsers
|   |-- parsers/                    # Structured section parser
|   |-- evidence/                   # Sentence-level evidence extraction/classification
|   |-- verification/               # JD extraction, skill discovery, scoring pipeline
|   |-- scoring/                    # Evidence/depth/consistency/confidence scoring
|   |-- scorer/                     # Legacy verification scorer
|   |-- signals/                    # Legacy skill/depth/consistency signals
|   |-- timeline/                   # Employment timeline parsing and analysis
|   `-- _qa_fixtures/               # Backend QA fixture documents
|-- backend_test_fixtures/          # Additional sample PDF/DOCX/image fixtures
|-- src/
|   |-- main.tsx                    # React entrypoint
|   |-- app/
|   |   |-- App.tsx                 # App provider and router shell
|   |   |-- routes.ts               # Dashboard routes
|   |   |-- context/                # Verification flow and API client logic
|   |   |-- components/             # Layout, evidence snippets, UI components
|   |   |-- pages/                  # Upload, Summary, Skills, Evidence, Reports, Settings, Help
|   |   `-- utils/                  # Frontend evidence normalization helpers
|   `-- styles/                     # Tailwind input, theme tokens, fonts
|-- pathai_design/                  # Next.js design-system prototype exported from Figma
|-- dist/                           # Vite production build output
|-- Dockerfile                      # Full-stack Node build + Python runtime image
|-- vercel.json                     # Vercel static frontend deployment config
|-- railway.json                    # Railway backend start command
|-- requirements.txt                # Python backend dependencies
|-- package.json                    # Root Vite frontend scripts and dependencies
|-- package-lock.json               # npm lockfile
`-- vite.config.ts                  # Vite config and base path support
```

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health check. |
| `POST` | `/extract-text` | Accepts a PDF or DOCX upload and returns normalized extracted text. |
| `POST` | `/score-resume` | Scores raw resume text with evidence, depth, consistency, JD compatibility, matched skills, missing skills, and action verbs. |
| `POST` | `/verify` | Runs the full JD-aware verification pipeline and returns risk, confidence, compatibility, verdict, claims, evidence, timeline, skills, and findings. |
| `GET` | `/` | Serves the built frontend when `dist/` exists. |
| `GET` | `/{full_path}` | SPA fallback for built frontend routes when `dist/` exists. |

### Example Verification Request

```bash
curl -X POST http://127.0.0.1:8000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Python developer with React and Docker experience...",
    "job_description": "We need a Python engineer with Docker and SQL.",
    "strictness": "medium",
    "cross_reference_sync": true
  }'
```

## OCR Pipeline

PathAI Verify uses a two-stage PDF extraction strategy:

1. **Embedded text extraction**: `backend/parser/pdf_parser.py` opens the PDF with PyMuPDF and extracts text from each page.
2. **OCR fallback**: If extracted text is below the 50-character threshold, the backend calls `extract_text_with_ocr()`.
3. **PDF rendering**: The OCR parser renders up to 10 pages at a higher scale using PyMuPDF.
4. **Preprocessing**: Each rendered page is converted through Pillow/OpenCV, grayscaled, and thresholded with Otsu binarization.
5. **Tesseract OCR**: pytesseract extracts English text from the processed image.
6. **Cleanup**: Page chunks are joined and blank lines are removed before normal resume normalization.

This enables scanned or image-only PDFs to enter the same verification pipeline as text-native PDFs.

## Installation

### Prerequisites

- Node.js 20 recommended. The Docker build uses `node:20-bookworm-slim`.
- Python 3.11 recommended. The Docker runtime uses `python:3.11-slim`.
- Tesseract OCR installed locally if you want OCR fallback outside Docker.
- npm for the root Vite app.

### Clone the repository

```bash
git clone <repository-url>
cd Path-ai
```

### Install frontend dependencies

```bash
npm ci
```

### Install backend dependencies

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS/Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

### Install Tesseract locally

Docker installs Tesseract automatically. For local backend OCR, install it on the host system:

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr

# Windows
winget install UB-Mannheim.TesseractOCR
```

If Tesseract is not available locally, text-native PDFs and DOCX files can still be parsed, but OCR fallback for scanned PDFs will fail or return empty text.

## Environment Variables

Only the following environment variables are referenced by the current codebase:

```env
# Frontend: send API calls to a separately hosted backend.
# In development, the frontend defaults to http://127.0.0.1:8000.
# In production, an empty value uses same-origin relative API paths.
VITE_API_BASE_URL=http://127.0.0.1:8000

# Frontend build base path. Defaults to /.
VITE_BASE_PATH=/

# Backend CORS allowlist. Comma-separated. If omitted, local dev origins and *.vercel.app are used.
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Hosting platforms commonly provide this automatically.
PORT=8000
```

There is no `OPENAI_API_KEY`, `DATABASE_URL`, or `JWT_SECRET` currently used in the repository.

## Running the Project

### Run the backend

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### Run the frontend

In a second terminal:

```bash
npm run dev
```

Open the Vite URL printed in the terminal, usually:

```text
http://localhost:5173
```

### Build the frontend

```bash
npm run build
```

### Serve the production frontend from FastAPI

After building, `dist/` exists and FastAPI can serve the SPA:

```bash
npm run build
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000
```

### Run with Docker

```bash
docker build -t pathai-verify .
docker run --rm -p 8000:8000 pathai-verify
```

The Docker image builds the Vite frontend, installs Python dependencies, installs `tesseract-ocr`, and starts Uvicorn.

## Resume Verification Flow

1. A user uploads a PDF/DOCX resume or pastes resume text directly.
2. If a file is uploaded, the backend validates size, extension, content type, and signature.
3. PDF/DOCX text is extracted. Scanned PDFs trigger OCR fallback.
4. The frontend sends extracted or pasted text plus the job description to `/verify`.
5. The verification pipeline normalizes text and groups content into resume sections.
6. Skills are discovered using curated aliases and section-aware sentence matching.
7. Job description requirements are extracted from the JD text.
8. Evidence snippets are classified as demonstrated, supported, mentioned, weak, or missing.
9. The engine computes compatibility, risk, confidence, weak areas, findings, timeline analysis, and verdict.
10. The dashboard renders summary metrics, claim details, evidence snippets, timelines, and report history.

## Verification and Scoring Logic

The main pipeline lives in `backend/verification/pipeline.py` and combines several scoring signals:

- **Compatibility score**: Based on overlap between job-description requirements and discovered resume skills, with a coverage bonus for broader skill evidence.
- **Claim evidence level**: Skill claims are evaluated using section context, implementation-heavy wording, evidence count, and whether a skill is required by the JD.
- **Confidence score**: Uses evidence-level confidence bands and weighted section scores so claims backed by experience/projects rank higher than bare skill-list mentions.
- **Risk score**: Increases for missing required skills, weak claims, unsupported claims, lack of action verbs, and cross-reference findings.
- **Timeline analysis**: Extracts year ranges, detects overlapping employment spans, possible gaps, and unusually long single spans.
- **Strictness**: `low`, `medium`, and `high` modes adjust penalties and evidence expectations.

Current analysis is deterministic and explainable. The code does not currently call an external LLM API.

## Dashboard Views

| Route | Purpose |
| --- | --- |
| `/` | Upload/paste resume and job description, then run verification. |
<img width="1917" height="1108" alt="image" src="https://github.com/user-attachments/assets/891cc015-b69e-4350-85af-6ea56ce82017" />

| `/summary` | Candidate verdict, confidence, compatibility, risk, findings, matched/missing skills, and action verbs. |
<img width="1904" height="1112" alt="image" src="https://github.com/user-attachments/assets/836da3bf-4b5a-4432-b19c-66d251abd1e2" />

| `/skills` | Searchable claim and skill breakdown with confidence and evidence tiers. |
<img width="1917" height="1112" alt="image" src="https://github.com/user-attachments/assets/0dc902a8-669e-4d24-b597-83ec3b54f055" />

| `/evidence` | Sentence-level evidence snippets, risk findings, timeline ranges, and skill first-seen insights. |
<img width="1917" height="1113" alt="image" src="https://github.com/user-attachments/assets/0a8ec989-8616-4c25-a7ca-41355b65e322" />

| `/reports` | Local scan history stored in browser `localStorage`. |
<img width="1917" height="1106" alt="image" src="https://github.com/user-attachments/assets/38b2457a-a4bd-4332-b9e1-a26d9241b7b9" />

| `/settings` | Strictness level and cross-reference sync settings. |
<img width="1917" height="1111" alt="image" src="https://github.com/user-attachments/assets/6828abe5-5e79-47b2-8ccb-36e422bd2e88" />

| `/help` | In-app help content. |
<img width="1919" height="1111" alt="image" src="https://github.com/user-attachments/assets/0ba8d982-b8f6-46bb-b02e-599dd9bd79fe" />


## Deployment

### Vercel

`vercel.json` is configured for the Vite frontend:

```json
{
  "installCommand": "npm ci",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite"
}
```

For a Vercel-only frontend deployment:

1. Set the project framework to Vite.
2. Use `npm ci` as the install command.
3. Use `npm run build` as the build command.
4. Use `dist` as the output directory.
5. Set `VITE_API_BASE_URL` to the deployed backend URL.
6. Set the backend `CORS_ORIGINS` to include the Vercel frontend domain.

Deployment note: Vercel will host the static frontend only with the current configuration. The FastAPI backend and OCR dependencies need a separate backend host unless the frontend is served by the FastAPI Docker image.

### Docker

The root `Dockerfile` supports a full-stack deployment:

- Builds the Vite frontend in a Node 20 stage.
- Installs Python dependencies in a Python 3.11 runtime.
- Installs `tesseract-ocr`.
- Copies `dist/` into the runtime image.
- Starts `uvicorn backend.main:app`.

This is the most complete deployment path for OCR because the container includes Tesseract.

### Railway

`railway.json` starts the backend with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Railway deployments should ensure Python dependencies from `requirements.txt` are installed and Tesseract is available if OCR fallback is required.

## Screenshots

_Add dashboard screenshots here._

Suggested captures:

- Upload and scan progress
- Summary verdict dashboard
- Skills and claims breakdown
- Evidence snippets and timeline analysis
- Reports history

## Design Provenance

The `pathai_design/` directory contains a Next.js design-system prototype for the PathAI Verify interface. The original mockup reference is:

https://www.figma.com/design/FjxvRSNA7R3lPypTfKBNPw/Revise-PathAI-Verify-Mockup

The production app in this repository is the root Vite application under `src/`.

## Future Improvements

- LLM-based semantic verification for richer project and responsibility reasoning
- Recruiter/admin dashboards with team-level report management
- Backend database for persistent candidates, scans, users, and audit trails
- Authentication and role-based access control
- LinkedIn, GitHub, portfolio, and certification verification integrations
- Fraud confidence calibration with labeled resume datasets
- Multilingual resume parsing and OCR language packs
- Exportable PDF reports for hiring teams
- Voice interview analysis and claim cross-checking against interview transcripts
- Automated test suite for parser fixtures, OCR fallback, and API contracts

## Contributing

Contributions are welcome. Please keep changes focused, tested, and aligned with the existing architecture.

1. Create a feature branch.
2. Install frontend and backend dependencies.
3. Run the relevant local checks before opening a pull request.
4. Document any new environment variables or deployment requirements.
5. Include screenshots for UI changes and sample API responses for backend changes.

Recommended checks:

```bash
npm run build
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

There is no dedicated automated test command checked into the repository yet.

## License

MIT License.
