# Architecture

Overview of the OCR web app. Legend: ✅ implemented · ⛏️ planned (see [PLAN-ocr-integration.md](PLAN-ocr-integration.md)).

## 1. Container topology (docker-compose)

```
                          ┌─────────────────────────────────────────────┐
                          │                Browser (SPA)                 │
                          │   React + Konva + Zustand + TanStack Query    │
                          └───────────────┬─────────────────────────────┘
                                          │ HTTP  /api/v1/*  (JWT Bearer)
                                          ▼
   ┌──────────────┐   Vite dev proxy  ┌───────────────────────────────┐
   │  frontend ✅ │ ───/api──────────▶│          backend ✅           │
   │ Vite :5173   │                   │      FastAPI (async) :8000     │
   └──────────────┘                   │  auth · documents · pages ·    │
                                       │  boxes · ocr endpoints         │
                                       └───┬───────────┬───────────┬────┘
                              async SQLA   │           │ enqueue   │ FileResponse
                              (asyncpg)    │           │ (Celery)  │ read/write
                                           ▼           ▼           ▼
                                   ┌────────────┐ ┌─────────┐ ┌──────────────┐
                                   │   db ✅    │ │ redis ⛏️│ │ uploads vol ✅│
                                   │ Postgres   │ │ broker +│ │ originals +  │
                                   │ :5432      │ │ results │ │ page PNGs    │
                                   └─────▲──────┘ └────┬────┘ └──────▲───────┘
                                         │ sync SQLA   │ pull tasks  │ read crops
                                         │ (psycopg2)  ▼             │
                                         │        ┌─────────────────────────┐
                                         └────────┤        worker ⛏️        │
                                                  │ Celery + RapidOCR/Paddle │
                                                  │  (ocr_page, ocr_region)  │
                                                  └───────────┬─────────────┘
                                                              │ first run downloads models
                                                              ▼
                                                     ┌──────────────────┐
                                                     │  ocr-models vol ⛏️ │
                                                     └──────────────────┘
```

**Two images:** the lean **API image** (no OCR deps — it only enqueues) and a separate ML-heavy **worker image** (`Dockerfile.worker`). The API writes via **async** SQLAlchemy; the worker writes via a **sync** session — both hit the same Postgres and the same `uploads` volume. Redis is **broker only** (Celery results unused — `OcrJob` is authoritative).

## 2. Data model (✅ exists · ⛏️ added for OCR)

```
User 1───* Document 1───* Page 1───* Box
                              │     │      x,y,w,h, text, source(manual|ocr),
                              │     │      confidence, order (+ label → bbox plan)
                              │     │      + ocr_job_id ⛏️  FK→OcrJob (SET NULL)  ← provenance
                              │     │
                              │     *───* OcrJob ⛏️   ← persistent, authoritative run record
                              │            kind(page|region) · pipeline(name) ·
                              │            status(queued|processing|done|failed) · error ·
                              │            region x,y,w,h · result_text/result_conf ·
                              │            box_count · task_id · created/started/finished_at
 (cascade delete all the way down)
Page: page_number, stored_path(PNG), width, height, ocr_status ⛏️ (denormalized cache)
Document: filename, mime_type, original_path, page_count
```

- All box geometry is in **page-PNG pixel space** — one coordinate system shared by the canvas, stored boxes, and OCR output.
- **`OcrJob` is the source of truth** for an OCR run (async, multi-pipeline, page+region, survives restarts). Ownership is checked via `OcrJob → Page → Document → owner_id` — no reliance on Celery's ephemeral, unauthenticated result store.
- **`Box.ocr_job_id`** records which run produced a box → scoped re-runs (re-running `paddle` replaces only paddle's boxes, keeps `tesseract` + manual) and pipeline badges in the UI.
- `Page.ocr_status` is a cheap denormalized mirror of the latest page-job status for list/badge rendering; `OcrJob` remains authoritative.
- Pipelines stay **code-defined** (registry) — never DB rows; `OcrJob.pipeline` just stores the chosen name.

## 3. Request flows

**Upload (✅):**
```
POST /documents (multipart)
  → save original → rasterize.py (PyMuPDF: PDF→PNG/page, or image→1 PNG)
  → create Document + Page rows → 201
```

**Full-page OCR (⛏️ async):**
```
POST /pages/{id}/ocr {pipeline?}
  → create OcrJob(kind=page, pipeline, status=queued); ocr_page.delay(job_id) → 202 {job_id}
  worker: job.status=processing → get_pipeline(name).detect(png)
          → delete boxes from prior jobs of this pipeline → insert ocr boxes (ocr_job_id=job)
          → job.status=done|failed (+box_count); page.ocr_status mirrors it
  frontend: poll GET /ocr/jobs/{job_id} (DB, ownership-checked) → on done, refetch boxes
```

**Region OCR (⛏️ async):**
```
POST /pages/{id}/ocr/region {x,y,w,h,pipeline?}
  → create OcrJob(kind=region, region, pipeline); ocr_region.delay(job_id) → 202 {job_id}
  worker: pipeline.recognize_region(png, box) → job.result_text/result_conf, status=done
  frontend: poll GET /ocr/jobs/{job_id} → fill the box's text
```

## 4. Pluggable pipeline seam (⛏️ the "flexible" core)

```
services/ocr/
├── base.py        OcrPipeline Protocol
│                    name · description · supports_region · languages
│                    detect(png) · recognize_region(png,x,y,w,h)
├── registry.py    @register_pipeline · get_pipeline(name) · available_pipelines()
├── stub.py        @register_pipeline  "stub"      ✅
├── tesseract.py   @register_pipeline  "tesseract" ⛏️
├── rapidocr.py    @register_pipeline  "rapidocr"  ⛏️  (default — PP-OCR on ONNXRuntime)
└── paddle.py      @register_pipeline  "paddle"    ⛏️  (optional — registers iff paddleocr imports)

add a pipeline  =  new class + @register_pipeline   →  auto-listed in GET /ocr/pipelines,
                                                        runnable by worker, selectable in UI
```

Selection is **per-request, UI-selectable**: `GET /ocr/pipelines` feeds a picker in the editor; the chosen name rides along with both OCR calls; `DEFAULT_OCR_PIPELINE` is the fallback.

## 5. Backend layout (✅ today + ⛏️ OCR)

```
backend/app/
├── main.py ✅                 FastAPI app, routers, CORS, /health
├── core/      config, security(JWT/bcrypt), deps(get_current_user) ✅
├── db/        async session ✅   +  sync session ⛏️ (for worker)
├── models/    user, document, page, box ✅   (+ ocr_job, page.ocr_status, box.ocr_job_id ⛏️)
├── schemas/   pydantic in/out ✅
├── api/v1/    auth · documents · pages · boxes · ocr ✅  (ocr → enqueue ⛏️)
├── services/
│   ├── rasterize.py ✅        PyMuPDF page rendering
│   └── ocr/  ⛏️               base · registry · stub · tesseract · paddle
└── worker/  ⛏️                celery_app.py · tasks.py (ocr_page, ocr_region)
```

## 6. Frontend layout (✅ + ⛏️ OCR hooks)

```
frontend/src/
├── pages/        Login · Register · Documents · Editor ✅
├── components/
│   ├── layout/AppShell ✅
│   ├── editor/  KonvaStage · BoxItem · BoxSidebar ✅   (Konva logic untouched)
│   └── ui/      shadcn (button, card, dialog, select…) ✅
├── stores/       authStore · editorStore ✅
├── hooks/        useDocuments · useBoxes · usePageImage ✅  +  useOcr ⛏️
└── lib/          api(fetch+JWT) · queryClient ✅
```

## Holding it together

- **One coordinate space** — page-PNG pixels everywhere (canvas, DB, OCR).
- **One box model** with a `source` discriminator, so manual + OCR boxes share all rendering/editing.
- **One pipeline interface** behind a registry, so OCR engines are swappable per request without touching the API, worker, or UI.

## Related docs

- [PLAN.md](PLAN.md) — Phase 1 scaffold
- [PLAN-frontend-rework.md](PLAN-frontend-rework.md) — shadcn UI rework
- [PLAN-bbox-management.md](PLAN-bbox-management.md) — manual box labels + precise editing
- [PLAN-ocr-integration.md](PLAN-ocr-integration.md) — PaddleOCR + Celery/Redis, pluggable pipelines
