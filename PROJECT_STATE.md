# Project Overview
- PathAI Verify is currently a deterministic resume/JD verification app.
- It extracts resume text from PDF/DOCX or pasted text, parses sections, detects skills/action verbs/timeline ranges, scores JD compatibility/risk/confidence, and renders recruiter-facing reports.
- No external AI/LLM call is implemented.
- No GitHub/LinkedIn/public-source verification is implemented, despite request fields and UI/help copy implying external evidence.
- Primary runnable product:
  - Frontend: root Vite React app in `src/app`.
  - Backend: FastAPI app in `backend/main.py`.
- Secondary/non-integrated design app:
  - `pathai_design/` is a separate Next.js prototype/design system with mocked data and independent dependencies.

# Tech Stack
- Frontend implemented:
  - React 18, Vite 6, TypeScript, React Router 7.
  - Tailwind CSS 4 via Vite plugin.
  - Radix/shadcn-style UI components, lucide-react, sonner, motion.
  - Client persistence via browser `localStorage`.
- Backend implemented:
  - Python FastAPI, Pydantic, Starlette CORS/static serving.
  - PyMuPDF for PDF text extraction/rendering.
  - python-docx for DOCX extraction.
  - pytesseract + Pillow + OpenCV for OCR fallback.
- Deployment files:
  - `Dockerfile` builds Vite frontend, installs Python deps and `tesseract-ocr`, serves FastAPI + static `dist`.
  - `railway.json` starts `uvicorn backend.main:app`.
  - `vercel.json` builds static Vite output only.
  - GitHub Actions deploys static Vite app to `gh-pages` with `VITE_BASE_PATH=/Path-ai/`.

# Architecture
- Implemented architecture flow:
```text
User
  -> Vite React dashboard (`src/app`)
    -> POST /extract-text for uploaded PDF/DOCX
      -> FastAPI validators
      -> PDF/DOCX parser
      -> OCR fallback for low-text PDFs
      -> normalized text
    -> POST /verify with text + JD + settings
      -> deterministic verification pipeline
      -> JSON report
    -> React context maps response into ScanResult
    -> localStorage history + report views
```
- Request flow diagram:
```text
Upload page
  -> pasted text?
      yes -> skip extraction
      no  -> FormData(file) -> /extract-text
  -> /verify JSON {
       text,
       job_description,
       strictness,
       cross_reference_sync
     }
  -> backend.analysis_engine.analyze_resume()
  -> backend.verification.pipeline.analyze_resume()
  -> frontend maps claims/evidence/timeline
  -> Summary / Skills / Evidence / Reports
```
- Backend module tree:
```text
backend/
  main.py                         FastAPI app, endpoints, static serving
  analysis_engine.py              Thin public wrapper around verification pipeline
  parser/
    pdf_parser.py                 PyMuPDF extraction + OCR fallback
    ocr_parser.py                 PDF page render + image preprocessing + Tesseract
    docx_parser.py                Paragraph/table extraction
    resume_parser.py              Legacy simple parser used by unreachable verify branch
  parsers/
    section_parser.py             Structured section/bullet/sentence parser
  verification/
    pipeline.py                   Main implemented verification engine
    jd_extract.py                 JD skill/action/domain extraction
    knowledge.py                  Skill aliases, verbs, strictness, weights
    normalize.py                  Text normalization
    skills_discovery.py           Skill counts from parsed sections
    years.py                      Years-of-experience regex extraction
  evidence/
    extractor.py                  Skill evidence hit selection
    classifier.py                 Evidence tier classification
    text.py                       Sentence/phrase/snippet helpers
  scoring/
    confidence.py                 Claim confidence bands + section weights
    scorer.py                     Legacy /score-resume scoring entry
    evidence.py/depth.py/consistency.py
  scorer/
    scoring.py                    Legacy verify scoring, now unreachable
  signals/
    *_signal.py                   Legacy signal scoring, now unreachable
  timeline/
    analysis.py                   Date span extraction, overlap/gap checks
```

# Frontend Structure
- `src/main.tsx`: mounts React app.
- `src/app/App.tsx`: wraps router with `VerificationProvider` and toast provider.
- `src/app/routes.ts`: routes under `DashboardLayout`.
- `src/app/context/VerificationContext.tsx`:
  - Chooses API base URL: `VITE_API_BASE_URL`, dev fallback `http://127.0.0.1:8000`, production same-origin.
  - Upload extraction via `/extract-text`.
  - Verification via `/verify`.
  - Maps backend snake_case fields into frontend `ScanResult`.
  - Stores history in `localStorage` key `pathai_history`.
  - Reads settings from `pathai_strictness` and `pathai_cross_reference_sync`.
- Pages implemented:
  - `/`: candidate name, job description, file upload, pasted resume text, scan progress.
  - `/summary`: verdict, risk/confidence/compatibility, matched/missing skills, findings.
  - `/skills`: searchable/filterable claim table and context cards.
  - `/evidence`: sentence snippets, evidence tiers, risk findings, timeline, overlap warnings.
  - `/reports`: local history browser/search; restores selected scan.
  - `/settings`: strictness and cross-reference sync settings.
  - `/help`: static help text; currently overstates external evidence.
- `src/app/components/ui/`: many generated UI primitives; only a subset is used.
- `pathai_design/`: separate Next.js app with mocked dashboard/upload/results; not wired to FastAPI.

# Backend Structure
- `backend/main.py` owns:
  - CORS setup.
  - Upload validation.
  - API request/response models.
  - Text extraction endpoint.
  - Scoring/verification endpoints.
  - Optional static serving of built `dist`.
- Main live verification path:
  - `/verify` -> `analyze_resume()` from `backend.analysis_engine`.
  - `analysis_engine.py` forwards to `backend.verification.pipeline.analyze_resume`.
- Legacy/dead path:
  - In `/verify`, code after the first `return JSONResponse(...)` is unreachable.
  - That unreachable branch uses `parse_resume_text`, `signals/*`, and `backend/scorer/scoring.py`.
  - `github` and `linkedin` fields exist on `VerifyRequest` but are not used in the live response path.
- `/score-resume` remains implemented but separate from frontend; it combines old signal scores with selected JD analysis fields.

# OCR / Parsing Pipeline
- Implemented:
  - Upload must have filename and pass extension/content-type checks.
  - Supported extraction endpoint file kinds: PDF and DOCX.
  - Max upload size: 10 MB.
  - PDF validation: bytes must start with `%PDF`.
  - DOCX validation: bytes must start with `PK`.
  - PDF text extraction uses PyMuPDF page `get_text("text")`.
  - If extracted PDF text is under 50 characters, OCR fallback runs.
  - OCR fallback:
    - Opens PDF with PyMuPDF.
    - Processes up to 10 pages.
    - Renders pages at 2x matrix.
    - Converts to grayscale and Otsu threshold via OpenCV.
    - Runs Tesseract English OCR.
  - DOCX extraction reads paragraphs plus table cells joined by ` | `.
  - Normalization lowercases text, removes control chars, collapses whitespace/newlines.
- Partial:
  - Upload UI accepts `.doc`, but backend rejects `.doc`; only PDF/DOCX are supported.
  - OCR has no per-request timeout, async offload, or resource guard beyond page cap/file size.
  - Image-only non-PDF uploads are not supported.
  - OCR fallback failures silently return empty OCR text and may produce 422.
- Planned/not implemented:
  - No image upload OCR endpoint.
  - No layout-aware PDF parsing beyond raw text and basic DOCX table cell extraction.

# Verification Engine
- Implemented:
  - Resume and JD text normalization.
  - Section parsing into skills, experience, projects, education, certifications, achievements, summary, other.
  - Skill discovery using static alias dictionary in `verification/knowledge.py`.
  - JD requirement extraction using same aliases plus domain/action/certification lists.
  - Evidence extraction:
    - Finds skill-matching sentences across parsed sections.
    - Prioritizes experience/projects/achievements over skills/summary/other.
    - Avoids duplicate snippets with a global snippet set.
    - Keeps up to 3 snippets per claim.
  - Evidence tiers:
    - `demonstrated`, `supported`, `mentioned`, `weak`, `missing`.
  - Pattern claims:
    - Years-of-experience statements.
    - Quantified achievements.
    - Project/build/deploy claims.
    - Leadership/team claims.
    - Certifications.
  - Consistency checks:
    - Skills primarily in keyword lists.
    - Weak/generic skill mentions.
    - Missing JD skills.
    - Buzzword sentences without action verbs.
  - Timeline:
    - Extracts year ranges such as `2020-2023`, `2020 to present`.
    - Reports overlaps, gaps, suspiciously long spans.
    - Estimates first-seen skill years only from implementation-heavy sections.
- Partial:
  - Section parsing is regex/heading based and can misbucket resumes with unusual formatting.
  - Evidence is sentence-level only; no source coordinates/page numbers.
  - Timeline uses year-only ranges, not months.
  - `present/current` is converted to hardcoded year `2026` in timeline analysis.
  - Skill taxonomy is static and narrow relative to real resumes.
- Planned/not implemented:
  - No external source verification.
  - No semantic matching/embedding/LLM claim extraction.
  - No recruiter workflow state beyond local browser history.

# Scoring Logic
- `/verify` scoring implemented in `backend/verification/pipeline.py`:
  - `compatibility_score`:
    - If JD exists: matched required skills / required JD skills * 76 + skill coverage bonus up to 18.
    - If no JD: based on number of detected resume skills, capped at 100.
  - Per-claim `confidence`:
    - Evidence-level bands:
      - demonstrated: 85-98
      - supported: 70-84
      - mentioned: 45-69
      - weak: 20-44
      - missing: 0-19
    - Blends section-weighted evidence score with band midpoint.
    - Adds deterministic hash jitter to avoid repeated flat scores.
  - `risk_score`:
    - Starts at `100 - compatibility`.
    - Adds penalties for inflated/missing skill claims.
    - Adds penalty for missing action verbs.
    - Adds cross-reference penalties when enabled.
    - Clamped 0-100.
  - `confidence`:
    - Weighted from compatibility, verified claim count, action verbs, and inflated claim count.
    - Clamped 0-100.
  - `verdict` thresholds in `backend/main.py`:
    - risk >= 70: `high_risk`
    - risk >= 35: `needs_review`
    - else `likely_consistent`
- `/score-resume` scoring implemented separately:
  - Old evidence/depth/consistency weighted confidence: 50/30/20.
  - Adds JD compatibility, matched/missing skills, action verbs from current analysis engine.
- Dead/legacy:
  - `backend/scorer/scoring.py` and `backend/signals/*` are imported but only used in unreachable `/verify` code.

# API Endpoints
- `GET /health`
  - Returns `{"status": "ok"}`.
- `POST /extract-text`
  - Multipart field: `file`.
  - Accepts PDF/DOCX only.
  - Returns `{ "text": cleaned_text }`.
  - Errors: 400 unsupported/invalid, 413 too large, 422 no extractable text/corrupt parser value error, 500 unexpected parser failure.
- `POST /score-resume`
  - JSON:
    - `text` required.
    - `job_description` optional.
    - `strictness`: low/medium/high.
    - `cross_reference_sync`: boolean.
  - Returns old signal scores plus compatibility/missing/matched/action verbs.
  - Not called by current frontend.
- `POST /verify`
  - JSON:
    - `text` required.
    - `job_description` optional.
    - `strictness`: low/medium/high.
    - `cross_reference_sync`: boolean.
    - `github`, `linkedin` accepted but unused.
  - Returns risk/confidence/compatibility/verdict/findings/claims/evidence/timeline/timeline_analysis/skill_timeline_insights/skills/action verbs/JD match fields/settings.
- Static serving:
  - If `dist/assets` exists, mounted at `/assets`.
  - If `dist` exists, `/` and catch-all serve SPA files.

# Data Storage
- Implemented:
  - No database.
  - No server-side persistence.
  - Scan history stored only in browser `localStorage`.
  - Settings stored only in browser `localStorage`.
  - Uploaded files are read in memory and not written to disk.
- Partial:
  - Generated IDs are client-side `PX-...` UUID fragments.
  - Stored report schema is normalized defensively on load.
- Planned/not implemented:
  - No users, auth, tenants, audit trail, report sharing, server report IDs, or retention policy.

# Deployment Setup
- Docker path:
  - Multi-stage build.
  - Node 20 builds Vite `dist`.
  - Python 3.11 runtime installs `tesseract-ocr` and Python requirements.
  - Uvicorn serves API and static frontend on `${PORT:-8000}`.
- Railway path:
  - Uses Nixpacks, not the Dockerfile.
  - Start command runs `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
  - Risk: Nixpacks may not install system `tesseract-ocr`; OCR can fail unless configured.
- Vercel path:
  - Static Vite build only.
  - Needs `VITE_API_BASE_URL` pointing to deployed backend; otherwise production frontend calls same-origin `/verify` and `/extract-text`, which will not exist on static Vercel.
- GitHub Pages path:
  - Static Vite deployment only.
  - Builds with `VITE_BASE_PATH=/Path-ai/`.
  - Needs external backend API URL; workflow does not set `VITE_API_BASE_URL`.
- Build/import check:
  - `npm run build` completed successfully.
  - `python -c "import backend.main"` completed successfully.

# Current Working Features
- IMPLEMENTED:
  - PDF/DOCX upload text extraction.
  - OCR fallback for low-text PDFs when Tesseract is installed.
  - Pasted resume text verification.
  - Required candidate name and job description in UI.
  - JD-based skill matching/missing skill detection.
  - Deterministic skill/action/timeline extraction.
  - Sentence-level evidence snippets and evidence tiers.
  - Risk/confidence/compatibility/verdict calculation.
  - Timeline overlap/gap/suspicious span reporting.
  - Search/filter in claims and report history.
  - Client-side scan history and settings.
  - FastAPI serving built SPA when `dist` exists.
- PARTIAL:
  - `/score-resume` exists but is not connected to UI.
  - Cross-reference sync is a deterministic internal consistency mode, not external source sync.
  - OCR works only for PDFs and depends on local/system Tesseract availability.
  - `pathai_design` provides design reference/mock UI but is not integrated.
- PLANNED/NOT IMPLEMENTED:
  - External GitHub/LinkedIn verification.
  - LLM/AI model-backed claim extraction or fraud analysis.
  - Server-side report persistence.
  - Authentication/authorization.
  - Admin/recruiter multi-user workflows.
  - Export/download/share verification reports.

# Partial / Incomplete Features
- UI says PDF/DOC/DOCX supported; backend supports PDF/DOCX only.
- Upload progress phases are UI timers, not backend progress events.
- Help page claims external evidence verification that does not exist.
- `VerifyRequest.github` and `linkedin` fields are unused.
- Some text says "AI analysis" or "AI-backed"; implementation is deterministic regex/rule scoring.
- Static deployment configs do not include backend wiring.
- Current history is lost when browser storage is cleared or user switches devices.
- Timeline "present" conversion is hardcoded to 2026.

# Technical Debt
- Dead/unreachable code in `/verify` after first return.
- Duplicate scoring systems:
  - Current pipeline scoring.
  - Legacy `backend/scoring/*`.
  - Legacy `backend/scorer/*` and `backend/signals/*`.
- Duplicate/near-duplicate parser naming:
  - `backend/parser/` and `backend/parsers/`.
- Generated `__pycache__` files are committed/tracked in repo.
- Dev log files are present at repo root (`backend.dev.*`, `frontend.dev.*`, `uvicorn.*`).
- Root package name is still `@figma/my-make-file`.
- Many UI component files are unused.
- Encoding artifacts appear in source strings (`â€¦`, `Â·`, `â€“`, etc.), likely from mojibake.
- `requirements.txt` has duplicate `typing_extensions` and unpinned packages.
- No automated test suite discovered despite fixture files.
- No lint/typecheck script beyond Vite build.
- `pathai_design` is a second frontend project with separate lockfile and dependencies, increasing monorepo ambiguity.

# Security Risks
- CORS default includes `https://*.vercel.app` while `allow_credentials=True`; broad preview-domain trust should be reviewed.
- No authentication or authorization on verification endpoints.
- No rate limiting.
- Upload parsing/OCR can be CPU/memory intensive; only file size and OCR page cap limit exposure.
- Error responses may expose parser exception strings.
- Resume text and PII are stored unencrypted in browser localStorage.
- No content security policy or privacy controls documented.
- No malware scanning for uploaded documents.
- No server-side audit logging or deletion/retention policy.

# Deployment Risks
- Railway/Nixpacks may miss `tesseract-ocr`; Dockerfile installs it but Railway config does not use Docker.
- Vercel and GitHub Pages deploy only frontend; API calls fail without `VITE_API_BASE_URL`.
- Same-origin production API mode only works when FastAPI serves `dist`.
- GitHub Actions uses Node 18, while Docker uses Node 20 and package uses Vite 6; build currently passed locally but versions are inconsistent.
- `requirements.txt` unpinned packages can change deploy behavior.
- Static `dist` serving is conditional on build artifact presence.
- Monorepo/root confusion:
  - Root Vite app is active product.
  - `pathai_design` Next app is separate and could be mistaken for production.
  - Deployment configs target different assumptions.
- `.gitignore` does not ignore Python `__pycache__`, `*.pyc`, or root dev logs.

# Immediate Priorities
- Remove or quarantine unreachable `/verify` legacy branch and unused `github/linkedin` request fields, or implement them.
- Decide deployment target:
  - Single FastAPI container serving Vite SPA, or
  - Static frontend plus separate API URL.
- Align deployment configs with that target.
- Add Tesseract installation/config for Railway if Railway remains supported.
- Fix UI truthfulness:
  - Remove "AI" and external evidence language unless implemented.
  - Remove `.doc` from accepted upload types or add `.doc` support.
- Add tests for:
  - `/extract-text` PDF/DOCX success and invalid files.
  - `/verify` scoring thresholds and missing skill behavior.
  - OCR fallback path with image-only PDF fixture.
  - Section/evidence parsing edge cases.
- Clean repo hygiene:
  - Remove committed caches/logs.
  - Expand `.gitignore`.
  - Rename package.
  - Pin Python dependencies.

# Suggested Next Architecture Steps
- Consolidate backend pipeline:
  - Keep `verification/pipeline.py` as source of truth.
  - Delete or archive legacy signal/scorer modules after tests cover current behavior.
- Introduce a typed report schema shared by backend/frontend:
  - Versioned JSON contract.
  - Stable claim/evidence/timeline objects.
- Add persistence boundary:
  - Database table for scans, candidates, reports, and evidence snippets.
  - Store original uploads only if retention/privacy policy allows it.
- Add async job model for OCR/large files:
  - Upload -> job ID -> background extraction/analysis -> polling/WebSocket/SSE status.
- Make extraction pluggable:
  - PDF text extractor.
  - OCR extractor.
  - DOCX extractor.
  - Future image/HTML/plain text extractors.
- Make verification pluggable:
  - Deterministic rule engine remains baseline.
  - External-source connectors can add evidence, not replace explainable scoring.
  - Optional LLM claim extraction should output structured claims with confidence and provenance.
- Add deployment profiles:
  - `docker-compose` or documented local dev.
  - Container production profile with Tesseract.
  - Static frontend profile requiring `VITE_API_BASE_URL`.
