# Plan: First-class Table Structure (shared box layer)

## Context

Today the two pipelines store results incoherently: OCR → flat `Box` rows (per page, FK provenance); extraction → an opaque `InvoiceDocument` JSON blob (per document), with table structure existing **only inside that blob** and linked back to geometry by soft `box_ids`. Re-running OCR orphans those ids, and the canvas can't show table structure.

Fix: make **table structure first-class in the box layer**, shared by both pipelines. Reframes the system into three layers:

```
OCR (text + flat boxes)  →  Structure (tables → cells with row/col)  →  Extraction (semantic JSON)
        Box(source=ocr)            Table + Box(table_id,row,col)              Extraction.data
```

A **cell is just a `Box`** with table membership + grid position — so structure lives in the same primitive the canvas already renders and the user already edits. Extraction then **reads persisted cells** instead of re-deriving them, and its `box_ids` point at real, FK-able cell rows.

## Schema (migration 0004, additive)

- **New `Table`** (`models/table.py`): `id`, `page_id` FK→pages (CASCADE, indexed), `order` (multiple tables/page), `x,y,w,h` (table bbox, nullable), `n_rows`, `n_cols` (nullable), `recognizer` (which engine produced it), `created_at`.
- **`Box` gains** (all nullable → flat boxes unaffected):
  - `table_id` FK→tables (`SET NULL`, indexed) — cell membership,
  - `row`, `col` (0-based, nullable), `row_span`, `col_span` (default 1), `is_header` (bool default false).
- A table **cell** = `Box` with `table_id`+`row`+`col` set (text = cell text). Flat word boxes keep `table_id=NULL`.

## Structure stage (new shared layer)

- **`TableRecognizer` registry** (third registry, same pattern as OCR/extractors) in `services/structure/`:
  - `base.py` — Protocol: `name`, `description`, `needs_ocr`; `recognize(image_path, ocr_boxes) -> list[RecognizedTable]` where each table carries cells `{row, col, row_span, col_span, is_header, x, y, w, h, text, confidence}`.
  - `heuristic.py` — the row/column **clustering currently inside the heuristic *extractor* moves here** (its natural home).
  - `ppstructure.py` — PaddleOCR PP-Structure TSR → cell grid (needs the `[paddle]` extra).
- **Worker task** `recognize_tables(job_id)` (reuses the `OcrJob` machinery with `kind="table"`, `pipeline=recognizer`): delete this recognizer's prior `Table`s + their cell boxes on the page → persist new `Table` rows + cell `Box` rows (`table_id,row,col`, `source="ocr"`).
- **Endpoints**: `GET /structure/recognizers`; `POST /pages/{id}/structure {recognizer?}` (enqueue); `GET /pages/{id}/tables` (tables + cells). Status polled via the existing `OcrJob` job endpoint.

## Extraction reads structure

- Extractors become **thin semantic mappers over persisted cells**: if a page has `Table`s, map columns→fields using `is_header` cells + column index; fill line items from cell rows. `box_ids` reference the real cell `Box` rows.
- **Fallback**: if no structure exists for the page, the extractor falls back to today's flat-box heuristic (so nothing regresses).
- `vlm` is unchanged (image→JSON), still validated by the shared `normalize.py`.

## Frontend (incremental)

- `GET /pages/{id}/tables` → render a **grid overlay** on the canvas (cells colored by table, header cells emphasized); a toggle to show/hide structure vs flat boxes.
- A "Detect tables" action (recognizer `Select`) alongside Run OCR, reusing the OCR status badge.

## What this resolves

- **One shared structured layer** — OCR and extraction no longer model the same document two disconnected ways.
- **Real provenance** — extracted fields reference persisted cell `Box` rows (FK), not soft ids buried in JSON.
- **Canvas can show/correct tables** — unlocks the deferred human-in-the-loop correction.

## Remaining caveat

Re-running OCR/structure still deletes+recreates boxes, so a *prior* extraction's references can go stale. Out of scope here; a follow-up can add a `stale` flag on `Extraction` when upstream layers change.

## Verification

1. Run OCR on an invoice → **Detect tables** (`ppstructure` or `heuristic`) → `GET /pages/{id}/tables` returns a table with `n_rows/n_cols` and cell boxes carrying `row/col`; grid overlay renders.
2. Re-run with the other recognizer → previous recognizer's cells replaced, flat OCR boxes untouched.
3. **Extract** → line items built from the persisted cells; each field's `box_ids` resolve to real cell rows.
4. Page with no structure → extraction still works via the flat-box fallback.
5. Delete the document → tables + cells cascade away.

## Build order

1. `Table` model + `Box` structural columns + migration 0004.
2. `structure/` registry + `heuristic` recognizer (move clustering out of the extractor) + `recognize_tables` task + endpoints.
3. Rework extractors to read cells (+ fallback).
4. `ppstructure` recognizer.
5. Frontend grid overlay + Detect-tables action.
