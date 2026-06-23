# Plan: Invoice Extraction (OCR boxes → consistent JSON)

## Context

OCR gives us text + boxes per page, but an invoice needs **structure**: which number belongs to which line-item, plus header fields and totals — emitted as a **consistent JSON** regardless of layout or engine. This is a distinct layer on top of OCR (table-structure recognition → semantic mapping → validation). We'll build it as a **pluggable Extractor registry** (mirroring the OCR pipeline registry), ship **three extractors to A/B** (`heuristic`, `ppstructure`, `vlm`), target a **full invoice schema** (header + line items + arithmetic validation), and for now **produce + export JSON only** (no in-editor review yet).

The thing that makes the JSON *consistent* is not the extractor — it's a **fixed Pydantic schema + a shared normalization/validation stage** that every extractor's output passes through.

## Core: the target schema (single source of "consistent")

`backend/app/schemas/invoice.py` — `InvoiceDocument`, schema-versioned:

```
ExtractedField[T]   = { value: T | None, confidence: float | None,
                        raw_text: str | None, box_ids: list[int] }   # provenance → canvas
LineItem            = { description, quantity, unit_price, line_total, tax_rate? }  # each an ExtractedField
Validation          = { arithmetic_ok: bool, checks: list[str], needs_review: bool }
InvoiceDocument     = { schema_version, vendor, invoice_number, date, due_date,
                        currency, line_items: list[LineItem],
                        subtotal, tax, total, amount_due, validation }
```

Every extractor returns this exact type → the API/DB/UI never branch on engine.

## Pluggable Extractor registry (mirror of OCR)

`backend/app/services/extract/`:
- `base.py` — `Extractor` Protocol: class attrs `name`, `description`, `needs_ocr: bool`, `languages`; method `extract(image_paths: list[str], ocr_boxes_by_page: list[list[OcrBox]]) -> InvoiceDocument`.
- `registry.py` — `@register_extractor`, `available_extractors()`, `get_extractor(name)` (lazy singletons). Same pattern as [services/ocr/registry.py](backend/app/services/ocr/registry.py).
- Built-ins (all three, self-registering; heavy imports lazy so the API can list them):
  - `heuristic.py` — **TSR by clustering** the existing OCR boxes: cluster by `y`→rows, derive column bands from the header row, assign tokens→cells, map columns→fields. No new deps. Transparent; best on regular templates. (CluSTi/ClusterTabNet approach.)
  - `ppstructure.py` — **PaddleOCR PP-StructureV3** table recognition → grid → map + validate. Needs the `[paddle]` extra. Robust grid recovery.
  - `vlm.py` — send page image (+ optional OCR text) to a **VLM/cloud** model that returns JSON; config-driven provider (`EXTRACT_VLM_*`: base url, model, key). Best for messy/Arabic; **must** pass the same validation to catch hallucination. `box_ids` left empty (or fuzzy-matched later).

## Shared normalization + validation stage

`backend/app/services/extract/normalize.py` — run on **every** extractor's raw output:
- Parse numbers (standard Western digits; handle decimal-separator variants like `1.234,56` vs `1,234.56`, and TND's 3-decimal millimes), dates, currency symbols → typed values. (No Arabic-Indic digit handling — Tunisian invoices use standard digits.)
- **Arithmetic reconciliation**: `Σ line_total ≈ subtotal`, `subtotal + tax ≈ total` (tolerance); populate `Validation.checks` and set `needs_review` on mismatch/low confidence.
- This is what guarantees uniform JSON across `heuristic` / `ppstructure` / `vlm`.

## Async + persistence (reuse the OcrJob pattern)

Extraction is slow (esp. VLM) → Celery task, like OCR.
- **Model/migration** `0003_add_extractions.py` (additive): `extractions` table — `id`, `document_id` FK→documents (CASCADE), `extractor`, `status` (`queued|processing|done|failed`), `error`, `schema_version`, `data` (JSONB), `needs_review`, `task_id`, timestamps. History per extractor → enables A/B comparison.
- **Task** `app/worker/tasks.py::extract_document(extraction_id)` (sync session): gather pages + their `source=ocr` boxes (run OCR first if absent and `needs_ocr`), call `get_extractor(name).extract(...)`, run `normalize`, store `data` + `needs_review`, set status.
- **Endpoints** ([api/v1/extract.py](backend/app/api/v1/extract.py)):
  - `GET /extract/extractors` → registry metadata.
  - `POST /documents/{id}/extract` `{extractor?}` → create `Extraction`, enqueue, `202 {extraction_id}`.
  - `GET /extractions/{id}` → status + `data` (ownership via document→owner).
  - `GET /documents/{id}/extractions` → history (for A/B).
  - `GET /extractions/{id}/export` → the JSON as a downloadable file.

## Frontend (produce + export only)

- `hooks/useExtract.ts`: `useExtractors()`, `useExtract(documentId)` (enqueue → poll extraction → toast).
- Editor/Documents: an **Extract** action + extractor `Select`; on done, a **read-only JSON viewer** (collapsible tree) with a **Download JSON** button and a `needs_review` badge. Optional side-by-side to compare extractors' outputs (A/B).
- No field-level correction UI yet (deferred — will tie to box labels in [PLAN-bbox-management.md](PLAN-bbox-management.md)).

## Dependencies

- `heuristic`: none beyond what we have.
- `ppstructure`: the existing `[paddle]` extra (+ PP-Structure table models, cached in `ocr-models` volume).
- `vlm`: a small HTTP/SDK client + `EXTRACT_VLM_*` config (cloud key or local VLM endpoint). Network egress from the worker.

## Verification (end-to-end)

1. `GET /extract/extractors` lists `heuristic`, `ppstructure`, `vlm`.
2. Upload an invoice → run OCR → **Extract** with `heuristic` → poll → JSON with header fields + line_items; `validation.arithmetic_ok` reflects totals.
3. Re-extract with `ppstructure` and `vlm` → three `extractions` rows for the same document → compare JSON (A/B). All conform to the identical schema.
4. Feed an invoice whose totals don't add up → `needs_review=true`, failing check listed.
5. Download JSON → valid `InvoiceDocument`. Numbers/dates normalized (standard digits; decimal-separator + TND millimes handled).
6. Cross-user `GET /extractions/{id}` → 404 (ownership via document→owner).

## Out of scope (later)

In-editor field correction/human-in-the-loop, box-label-driven field hints, multi-page line-item stitching edge cases, per-field box provenance for the VLM extractor, training/fine-tuning.
