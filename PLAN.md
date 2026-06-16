# Plan: OCR Web App — Phase 1 Scaffold (no OCR engine yet)

## Context

We're building a document OCR web application from an empty directory. Per the agreed direction, **Phase 1 builds the full web app shell and core functionality first** — auth, document upload/storage, and the interactive Konva editor — while deliberately **stubbing the OCR engine** behind a clean interface so it can be dropped in later without reworking the UI or data model.

The Konva canvas does **both**: users draw annotation zones on a document image, *and* view/edit detected text boxes (which, until the engine exists, come from manual entry). This dual role drives the data model: a `Box` must carry geometry + text + a `source` field (`manual` | `ocr`) so the same rendering/editing code serves both today's manual boxes and tomorrow's OCR output.

Outcome of Phase 1: a runnable `docker-compose up` stack where a user can register, log in, upload an image, draw/edit boxes on it via Konva, persist them, and see them on reload — with the OCR call returning an empty list (no-op).

## Tech Stack

- **Frontend**: Vite + React + TypeScript + react-konva + Zustand + TanStack Query + Tailwind
- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + Alembic
- **Auth**: JWT + python-jose + passlib/bcrypt
- **Storage**: Local filesystem (mounted volume)
- **DB**: PostgreSQL (Docker)
- **Infra**: docker-compose

## Repository Layout (monorepo)

```
ocr/
├── docker-compose.yml          # postgres + backend + frontend
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml          # deps: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg,
│   │                           #       alembic, python-jose[cryptography], passlib[bcrypt],
│   │                           #       pydantic-settings, python-multipart, pillow
│   ├── alembic.ini
│   ├── alembic/                # env.py + versions/
│   └── app/
│       ├── main.py             # FastAPI app, CORS, router include, /health
│       ├── core/
│       │   ├── config.py       # pydantic-settings: DB url, JWT secret, upload dir, CORS
│       │   ├── security.py     # hash/verify pwd, create/decode JWT
│       │   └── deps.py         # get_db, get_current_user
│       ├── db/
│       │   ├── base.py         # DeclarativeBase
│       │   └── session.py      # async engine + sessionmaker
│       ├── models/             # User, Document, Box (SQLAlchemy 2.0 Mapped[] style)
│       ├── schemas/            # Pydantic v2 request/response models
│       ├── api/v1/
│       │   ├── auth.py         # POST /register, POST /login (OAuth2 password -> JWT)
│       │   ├── documents.py    # CRUD + file upload + GET image bytes
│       │   ├── boxes.py        # CRUD boxes for a document (bulk save)
│       │   └── ocr.py          # POST /documents/{id}/ocr  -> calls OcrEngine stub
│       └── services/
│           └── ocr/
│               ├── base.py     # OcrEngine Protocol: detect(image_path) -> list[OcrBox]
│               └── stub.py     # StubOcrEngine returning []
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts          # dev server + /api proxy to backend
    ├── tailwind.config.js / postcss.config.js
    ├── index.html
    └── src/
        ├── main.tsx, App.tsx, index.css
        ├── lib/
        │   ├── api.ts          # fetch wrapper, attaches JWT, base /api/v1
        │   └── queryClient.ts  # TanStack Query client
        ├── stores/
        │   ├── authStore.ts    # Zustand: token, user, login/logout (persist token)
        │   └── editorStore.ts  # Zustand: boxes in-edit, selectedId, tool, zoom/pan
        ├── hooks/              # useDocuments, useDocument, useBoxes (TanStack Query)
        ├── pages/
        │   ├── LoginPage.tsx, RegisterPage.tsx
        │   ├── DocumentsPage.tsx   # list + upload
        │   └── EditorPage.tsx      # the Konva workspace
        └── components/
            ├── ProtectedRoute.tsx
            ├── UploadDropzone.tsx
            └── editor/
                ├── KonvaStage.tsx      # Stage/Layer, image, zoom/pan
                ├── BoxLayer.tsx        # renders Rect + Transformer per box
                ├── BoxItem.tsx         # draggable/resizable box, click to select
                ├── DrawingLayer.tsx    # drag-to-create new box
                └── BoxSidebar.tsx      # list boxes, edit text, source badge, save
```

## Data Model

- **User**: `id`, `email` (unique), `hashed_password`, `created_at`.
- **Document**: `id`, `owner_id` (FK User), `filename`, `stored_path`, `mime_type`, `width`, `height` (px, read on upload via Pillow), `status` (`uploaded` | `processing` | `done`), `created_at`.
- **Box**: `id`, `document_id` (FK), `x`, `y`, `w`, `h` (floats, image-pixel coords), `text` (nullable), `source` (`manual` | `ocr`), `confidence` (nullable float), `order` (int), `created_at`, `updated_at`.

Cascade delete boxes with their document. All geometry stored in **image pixel coordinates** (not canvas coords) so the model is zoom/pan-independent; the frontend converts via the Konva stage scale.

## API (prefix `/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | create user |
| POST | `/auth/login` | OAuth2 password form → `{access_token}` |
| GET | `/auth/me` | current user |
| GET | `/documents` | list current user's docs |
| POST | `/documents` | multipart upload (image) → Document |
| GET | `/documents/{id}` | metadata |
| GET | `/documents/{id}/file` | raw image bytes (auth-checked) |
| DELETE | `/documents/{id}` | delete doc + file + boxes |
| GET | `/documents/{id}/boxes` | list boxes |
| PUT | `/documents/{id}/boxes` | bulk replace/save boxes (simplest for canvas editor) |
| POST | `/documents/{id}/ocr` | run `OcrEngine.detect()` → persist boxes with `source=ocr` |

The `/ocr` endpoint is wired end-to-end but backed by `StubOcrEngine`, which **returns an empty list** in Phase 1 (no-op). The full request/response/persistence path exists and works; it simply produces no boxes until a real engine lands. Swapping in a real engine later = one new class + a config switch in `services/ocr/__init__.py`.

## Konva Editor Behavior

- Load document image into a Konva `Image` on a `Stage`; support wheel-zoom and drag-pan.
- **Two tools** (toolbar): *Select* (move/resize existing boxes via `Transformer`) and *Draw* (drag to create a new `manual` box).
- Boxes rendered from `editorStore`; each editable, selectable, deletable.
- Sidebar lists boxes with an editable text field, a `source` badge (manual/ocr), and confidence if present.
- "Run OCR" button calls `/ocr`, merges returned `ocr` boxes into the editor (none in Phase 1).
- "Save" does `PUT /boxes` (bulk). Coordinates converted canvas↔image on render/save.

## Auth Approach

JWT (HS256) via python-jose; passlib/bcrypt for hashing. Token returned on login, stored in Zustand `authStore` (persisted to localStorage), attached as `Authorization: Bearer` by `lib/api.ts`. `get_current_user` dependency decodes and loads the user. `ProtectedRoute` guards `/documents` and `/editor`.

## docker-compose

- `db`: postgres:16, named volume, healthcheck.
- `backend`: builds `backend/`, runs `alembic upgrade head` then `uvicorn`, depends_on db healthy, mounts an `uploads/` volume, exposes 8000.
- `frontend`: builds `frontend/`, Vite dev server on 5173, proxies `/api` → backend.
- `.env.example` documents `POSTGRES_*`, `JWT_SECRET`, `BACKEND_CORS_ORIGINS`.

## Build Order (implementation sequence)

1. Scaffold repo skeleton + `docker-compose.yml` + `.env.example` + README.
2. Backend: config/db/security → models → Alembic initial migration → auth endpoints.
3. Backend: documents (upload + file serve) → boxes (bulk) → ocr stub endpoint.
4. Frontend: Vite/Tailwind setup → api client + query client + auth store → login/register + ProtectedRoute.
5. Frontend: DocumentsPage (list + upload).
6. Frontend: EditorPage + Konva components (stage, draw, edit, sidebar, save, run-OCR).
7. Wire-through pass + README run instructions.

## Verification (end-to-end)

1. `cp .env.example .env`, `docker-compose up --build` → all three services healthy; `GET /health` 200; alembic migration applied.
2. Register a user, log in (token persisted; refresh keeps session).
3. Upload an image on DocumentsPage → appears in list with correct dimensions.
4. Open editor → image renders; zoom/pan work.
5. Draw a box, edit its text, resize/move it, save → reload page → box persists at correct position.
6. Click "Run OCR" → stub path executes without error and returns 0 boxes (no-op); no error surfaces in the UI.
7. Delete a document → file, DB row, and boxes removed.

## Out of Scope (Phase 1)

Real OCR engine, multi-page/PDF documents, box ordering/reading-order export, text export formats, user roles/sharing, tests beyond a smoke test (can add pytest skeleton if desired).
