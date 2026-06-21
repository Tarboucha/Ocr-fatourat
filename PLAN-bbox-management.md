# Plan: Manual Bounding-Box Management (labels + precise editing)

## Context

The editor can already draw, select, drag-move, Transformer-resize, text-edit, and delete a single box per page (see [BoxItem.tsx](frontend/src/components/editor/BoxItem.tsx), [KonvaStage.tsx](frontend/src/components/editor/KonvaStage.tsx), [BoxSidebar.tsx](frontend/src/components/editor/BoxSidebar.tsx), [editorStore.ts](frontend/src/stores/editorStore.ts)). For an invoice OCR tool ("fatourat"), that's not enough to *manage* boxes: users need to (1) **label** each box by field type so detected regions mean something, and (2) **edit geometry precisely** — exact coordinates, keyboard nudging, and undo/redo so mistakes are cheap.

This round adds, per the agreed scope: a **`label` field** on boxes with a labeling UI, **numeric X/Y/W/H inputs + arrow-key nudge**, **undo/redo**, and **bounds/min-size clamping** as a baseline. Out of scope: multi-select, duplicate/copy-paste, reading-order UI.

## Backend changes

- **[models/box.py](backend/app/models/box.py)**: add `label: Mapped[str | None]` (nullable `String`). Freeform on the backend; the frontend constrains it to a palette but the API stays flexible.
- **[schemas/box.py](backend/app/schemas/box.py)**: add `label: str | None = None` to `BoxBase` (so it flows through `BoxIn`/`BoxOut` automatically).
- **[api/v1/boxes.py](backend/app/api/v1/boxes.py)**: include `label=b.label` when constructing `Box` rows in `replace_boxes`.
- **New migration** `backend/alembic/versions/0002_add_box_label.py`: `op.add_column("boxes", sa.Column("label", sa.String(), nullable=True))` + drop in `downgrade`. **Additive** — no volume wipe needed; `alembic upgrade head` applies it on container start.

## Frontend changes

### Label palette
- **New [lib/labels.ts](frontend/src/lib/labels.ts)**: invoice field palette as `{ key, name, color }[]` — e.g. Vendor, Date, Invoice #, Subtotal, Tax, Total, Line item, Other. Single source of truth for label names + colors.
- **types.ts**: add `label: string | null` to `Box`, `EditorBox`, `BoxInput`.

### editorStore.ts — geometry + history
- Add `imageSize: { width, height } | null` + `setImageSize` (used to clamp boxes to the page-image bounds).
- Add **undo/redo**: `past: EditorBox[][]`, `future: EditorBox[][]`, `pushHistory()` (snapshots current boxes → `past`, clears `future`), `undo()`, `redo()`. `loadBoxes` resets history; `undo`/`redo` set `dirty=true`.
- Centralize **clamping** in a `clampBox(box, imageSize)` helper (x,y ≥ 0; x+w ≤ W; y+h ≤ H; w,h ≥ MIN=4). Apply in `addBox`, `updateBox`, and nudge.
- `addBox`/`removeBox` call `pushHistory()` themselves (discrete actions). `updateBox` does **not** auto-snapshot (it fires rapidly during drag/typing); callers snapshot once at the *start* of an interaction.

### Interaction wiring
- **BoxItem.tsx**: add `onInteractStart` prop fired on `onDragStart`/`onTransformStart` → calls `pushHistory()` once per drag/resize. Color the rect/label by `label` color when set, else fall back to the existing `source` color. Render the label name as a small tag at the box's top-left.
- **KonvaStage.tsx**: pass `onInteractStart`; clamp newly drawn boxes to `imageSize`; call `setImageSize` from the loaded image.
- **BoxSidebar.tsx**: for the selected box add — a **label `<select>`** (palette + "unlabeled"), **numeric X/Y/W/H inputs** (integer, clamped; snapshot history on focus), and **Undo/Redo buttons** (disabled when stacks empty). Keep the existing text + remove controls; show the label tag/color on each list item.
- **EditorPage.tsx**:
  - Set `imageSize` from `currentPage` / loaded image.
  - Keyboard: **arrow keys** nudge the selected box (Shift = 10px), **Ctrl+Z** undo, **Ctrl+Shift+Z / Ctrl+Y** redo — all gated by the existing "not typing in an input" guard so the browser still handles text-field undo. Nudge snapshots history once per keypress.
  - Include `label` in the `BoxInput[]` save payload.

### History snapshot strategy (avoids noisy undo)
- Drag / resize → one snapshot at interaction start (`onInteractStart`).
- Text + numeric edits → snapshot on **field focus** (one undo entry per editing session), letting the browser handle in-field text undo.
- Add / delete / label-change / nudge → one snapshot per action.

## Critical files
`backend/app/models/box.py`, `backend/app/schemas/box.py`, `backend/app/api/v1/boxes.py`, `backend/alembic/versions/0002_add_box_label.py`, `frontend/src/lib/labels.ts` (new), `frontend/src/types.ts`, `frontend/src/stores/editorStore.ts`, `frontend/src/components/editor/{BoxItem,KonvaStage,BoxSidebar}.tsx`, `frontend/src/pages/EditorPage.tsx`.

## Rebuild

No volume wipe (migration is additive). Backend deps unchanged → fast rebuild.
```
docker compose up --build
```

## Verification (end-to-end)

1. Open a document → draw a box → pick a label in the sidebar → box + tag recolor to the label color.
2. Edit X/Y/W/H numerically → box moves/resizes live; values clamp at image edges; W/H can't go below 4.
3. Select a box → arrow keys nudge 1px, Shift+arrow 10px; box can't leave the image bounds.
4. Move/resize/label/delete/add, then **Ctrl+Z** repeatedly → each action reverts in order; **Ctrl+Shift+Z** re-applies. Undo/Redo buttons reflect availability.
5. Save → reload page → labels and geometry persist; label colors restored.
6. Switch PDF pages → history resets per page; each page's labels are independent.
