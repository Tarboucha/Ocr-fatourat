# Plan: OCR Integration (RapidOCR/Paddle + Celery/Redis, full-page + region)

## Context

The app has the full annotation shell but OCR is a no-op stub ([services/ocr/stub.py](backend/app/services/ocr/stub.py)) behind the `OcrEngine` Protocol ([services/ocr/base.py](backend/app/services/ocr/base.py)), and `POST /pages/{id}/ocr` runs inline ([api/v1/ocr.py](backend/app/api/v1/ocr.py)). OCR is CPU-bound and slow (~2–30s/page), so it must move off the request path. We're integrating real OCR behind a **pluggable pipeline registry**, run by a **Celery worker** over **Redis**, supporting **two modes**: full-page auto-detect and on-demand region OCR. The default engine is **RapidOCR** (PP-OCR models on ONNXRuntime — same accuracy as PaddleOCR, ~5× smaller image); a heavier **PaddleOCR** pipeline is registered too (when its deps are present) so the two can be **A/B'd on real invoices**. Boxes already carry `source=ocr` + `confidence` and live in page-pixel coordinates — the contract is mostly in place.

## Architecture

```
Browser ──POST /pages/{id}/ocr──▶ FastAPI (create OcrJob, enqueue) ──▶ Redis ──▶ Celery worker
   ▲                                  (lean API image)              (broker only)  │ RapidOCR / Paddle
   └────── poll GET /ocr/jobs/{id} ◀── FastAPI ◀── worker writes boxes + job status ┘ (sync DB session)
```

- **New docker-compose services**: `redis` (**broker only** — Celery results are unused because `OcrJob` in Postgres is authoritative) and `worker`. The worker is a **separate, ML-heavy image** (`backend/Dockerfile.worker`) so the **API image stays lean** (no OCR deps). It runs `celery -A app.worker.celery_app worker --concurrency=1`, shares the `uploads` volume + DB, plus an `ocr-models` volume to cache downloaded model files.
- **Sync DB in the worker**: Celery tasks are sync; running async SQLAlchemy inside them is the classic footgun. Add a **sync engine/session** (`postgresql+psycopg2://`, derived from `DATABASE_URL`) in [db/session.py](backend/app/db/session.py) and use it in tasks. API stays async.

## Backend changes

- **Deps**:
  - **API image** ([pyproject.toml](backend/pyproject.toml)): add only `celery[redis]`, `redis`, `psycopg2-binary` — no OCR libs. API just enqueues.
  - **Worker image** (`Dockerfile.worker`, optional `[ocr]` extra in pyproject): `rapidocr-onnxruntime`, `opencv-python-headless`, `pillow`. RapidOCR uses **PP-OCR detect+recognize** (not PP-Structure). The heavy `paddleocr`+`paddlepaddle` are an **optional `[paddle]` extra**; the `paddle` pipeline self-registers only if importable, so the default worker image stays light (~few hundred MB). First OCR downloads model files into the `ocr-models` volume (slow once).
- **Config** ([core/config.py](backend/app/core/config.py)): add `REDIS_URL`, `DEFAULT_OCR_PIPELINE` (default `rapidocr`), and a derived `sync_database_url`.
- **Flexible pipeline registry** (core requirement — adding a pipeline = write a class + register it, nothing else changes):
  - Extend the Protocol in [services/ocr/base.py](backend/app/services/ocr/base.py) into `OcrPipeline` with capability metadata + two methods:
    - class attrs: `name`, `description`, `supports_region: bool`, `languages: list[str]`.
    - `detect(image_path) -> list[OcrBox]` (full-page) and `recognize_region(image_path, x, y, w, h) -> OcrBox` (crop → OCR → coords offset back to page space).
  - New `services/ocr/registry.py`: a `@register_pipeline` decorator populating a `name → class` map, plus `available_pipelines() -> list[metadata]` and `get_pipeline(name) -> OcrPipeline` (lazy-instantiated/cached). New pipelines self-register on import; [services/ocr/__init__.py](backend/app/services/ocr/__init__.py) imports the built-ins so they register.
  - Each pipeline may be multi-stage internally (deskew → detect → recognize → post-process); the registry only cares about the Protocol.
  - Built-ins this round: `stub` (existing), `tesseract` (light fallback), **`rapidocr`** (`services/ocr/rapidocr.py`, default — PP-OCR det+rec on ONNXRuntime; quad polygons → axis-aligned `x,y,w,h` + `confidence`), and **`paddle`** (`services/ocr/paddle.py`, optional — self-registers only if `paddleocr` imports). Same model family ⇒ `rapidocr` and `paddle` are directly comparable on real invoices.
  - `DEFAULT_OCR_PIPELINE` in config = `rapidocr`; it's the fallback when a request doesn't name one.
- **Model/migration** — additive `0002_add_ocr_jobs.py` (no volume wipe):
  - New **`OcrJob`** table — authoritative run record: `id`, `page_id` FK→pages (CASCADE), `kind` (`page|region`), `pipeline` (registry name), `status` (`queued|processing|done|failed`), `error`, region `x/y/w/h` (nullable), `result_text`/`result_confidence` (region), `box_count` (page), `task_id`, `created_at`/`started_at`/`finished_at`. Ownership via `page → document → owner_id`.
  - `boxes.ocr_job_id` FK→ocr_jobs (nullable, `ON DELETE SET NULL`) — provenance.
  - `pages.ocr_status` (`idle|queued|processing|done|failed`, default `idle`) — denormalized mirror of the latest *page* job for cheap list/badge rendering; `OcrJob` stays authoritative.
- **Celery app** `app/worker/celery_app.py` (**broker only**, no result backend; `task_acks_late=True`, `task_reject_on_worker_lost=True`, a `task_time_limit`/soft limit so a bad image can't hang the worker); **model warmup** on `worker_process_init` so the first OCR isn't a cold-load. **tasks** `app/worker/tasks.py` take a **`job_id`** and use the **sync** session:
  - `ocr_page(job_id)`: load job+page → `status=processing` (+ mirror to `page.ocr_status`) → `get_pipeline(job.pipeline).detect()` → **delete boxes whose `ocr_job` used the same pipeline on this page** (keep manual + other pipelines) → insert ocr boxes with `ocr_job_id=job` → `status=done`, `box_count=n`; on error `status=failed` + `error`.
  - `ocr_region(job_id)`: `pipeline.recognize_region()` → **update the target box server-side** (text, `source=ocr`, `confidence`, `ocr_job_id`) so provenance matches full-page boxes; also store `result_text`/`result_confidence` on the job; `status=done`. Reject up-front if `pipeline.supports_region` is false.
- **Endpoints** ([api/v1/ocr.py](backend/app/api/v1/ocr.py)):
  - `GET /ocr/pipelines` → `available_pipelines()` metadata (`name`, `description`, `supports_region`, `languages`) so the UI can list + adapt.
  - `POST /pages/{id}/ocr` `{pipeline?}` → validate name against registry; **guard: 409 if an active (`queued|processing`) page job already exists for this page+pipeline**; else **create `OcrJob`**, `ocr_page.delay(job.id)`, return `202 {job_id}`.
  - `POST /pages/{id}/ocr/region` `{x,y,w,h,pipeline?,box_id?}` → create region `OcrJob` (worker fills `box_id` if given, else creates a new `source=ocr` box), `ocr_region.delay(job.id)`, `202 {job_id}`. Frontend refetches boxes on `done`.
  - `GET /ocr/jobs/{job_id}` → **read the DB row, ownership-checked** via page→document→owner → `{status, error, result_text, result_confidence, box_count}`. (No Celery `AsyncResult`, no Redis dependency, no auth hole.)
  - `GET /pages/{id}` includes `ocr_status` for the toolbar badge.

## Frontend changes

- **New `useOcr.ts`**: `usePipelines()` (`GET /ocr/pipelines`); `useRunOcr` POSTs (with the selected pipeline) → gets `job_id` → polls `page.ocr_status` (or the job) via TanStack Query `refetchInterval` while `queued|processing`; on `done`, invalidate the page's boxes query so new `source=ocr` boxes load. Toasts for done/failed.
- **Pipeline picker**: a small `Select` in the editor toolbar listing available pipelines (default = `DEFAULT_OCR_PIPELINE`); its value is passed to both OCR actions. Region action is disabled for pipelines whose `supports_region` is false.
- **Region OCR** in [EditorPage.tsx](frontend/src/pages/EditorPage.tsx) / [BoxSidebar.tsx](frontend/src/components/editor/BoxSidebar.tsx): an "OCR this box" action on the selected (saved) box → POST region with its geometry + `box_id` + chosen pipeline → poll job → on `done`, refetch boxes (the worker filled the box server-side).
- **Status UI**: page OCR status (spinner/badge) in the editor toolbar; "Run OCR" disabled while processing.

> Note: the pipeline `Select` needs the shadcn `select` component — `npx shadcn@latest add select` (I'll give the command when we build).

## What stays unchanged

Konva canvas/box geometry, auth, routing, the `Document→Page→Box` model and cascade, page-pixel coordinate system, the existing `source/confidence` fields.

## Tests

Keep `stub` for fast CI. Unit-test: the registry (register/list/get + unknown name), the quad→AABB coordinate conversion, and `ocr_page`/`ocr_region` against a **fake pipeline** (no ML deps) to exercise status transitions, scoped box replacement, and the double-run guard.

## Rebuild

New services; the **worker** image carries the OCR deps (API stays lean). First OCR downloads model files once (cached in the `ocr-models` volume).
```
docker compose up --build
```

## Verification (end-to-end)

1. `docker compose ps` shows `db`, `redis`, `backend`, `worker`, `frontend` healthy; worker logs "ready".
2. Open a page → **Run OCR** → an `OcrJob` row is created; status goes `queued → processing → done`; emerald `source=ocr` boxes appear with text + confidence + `ocr_job_id`. Re-running the same pipeline replaces only that pipeline's boxes; manual boxes and other pipelines' boxes survive.
2b. `GET /ocr/jobs/{id}` as another user → `404` (ownership enforced via page→document→owner).
2c. Click **Run OCR** twice fast → second request returns `409` (active-job guard), no duplicate run.
3. Draw + save a box → **OCR this box** → after the job, the box's text is filled server-side (`source=ocr`, confidence shown).
4. Kill OCR on a bad image → status `failed`, error toast; app stays usable; worker time-limit prevents a hang.
5. `GET /ocr/pipelines` lists `stub`, `tesseract`, `rapidocr` (and `paddle` if its extra is installed); switch the toolbar picker and re-run → different engine, same flow — proving the registry seam. Adding a new pipeline class + `@register_pipeline` makes it appear with no other changes. A/B `rapidocr` vs `paddle` on the same invoice to compare.

## Out of scope (later)

Field labels (see [PLAN-bbox-management.md](PLAN-bbox-management.md)), key-value/table extraction (PP-StructureV3 layout), GPU, websockets/SSE live updates, multi-worker autoscaling, cloud-engine adapter.
