# OCR Web App

A document OCR web application. **Phase 1** ships the full web app shell —
authentication, image upload/storage, and an interactive Konva editor for
drawing and editing text-region boxes — with the OCR engine **stubbed** behind
a clean interface so a real engine (Tesseract / PaddleOCR / cloud) can be
dropped in later without touching the UI or data model.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Vite + React + TypeScript + react-konva + Zustand + TanStack Query + Tailwind |
| Backend | FastAPI + SQLAlchemy 2.0 (async) + Alembic |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Storage | Local filesystem (docker volume) |
| DB | PostgreSQL |
| Infra | docker-compose |

## Quick start (Docker)

```bash
cp .env.example .env        # adjust JWT_SECRET for anything non-local
docker compose up --build
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

The backend container runs `alembic upgrade head` before starting, so the
schema is created automatically on first boot.

## Usage

1. Open the frontend, **Register** an account (auto-logs you in).
2. On the Documents page, **upload an image** (PNG/JPEG/WebP/BMP/TIFF).
3. Click a document to open the **editor**:
   - **Select / Pan** — drag to pan, scroll to zoom, click a box to select,
     drag/resize it, `Del` to remove.
   - **Draw box** — drag on the image to create a new manual box.
   - Edit box text in the right sidebar; the `source` badge shows
     `manual` vs `ocr`.
   - **Save** persists all boxes (bulk replace).
   - **Run OCR** calls the engine — in Phase 1 the stub returns no boxes.

## Project layout

```
backend/   FastAPI app, SQLAlchemy models, Alembic migrations, OCR service
frontend/  Vite/React app: pages, hooks (TanStack Query), Zustand stores, Konva editor
```

Key seams:
- `backend/app/services/ocr/` — `OcrEngine` protocol + `StubOcrEngine`. Add a
  real engine class and switch it in `services/ocr/__init__.py`.
- `Box.source` (`manual` | `ocr`) — one model/UI path serves both hand-drawn
  boxes and future OCR output. Geometry is stored in **image-pixel coordinates**,
  so it is independent of zoom/pan.

## Local development without Docker

Backend:
```bash
cd backend
pip install -e .
export DATABASE_URL=postgresql+asyncpg://ocr:ocr@localhost:5432/ocr
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
# Point the dev proxy at your local backend:
VITE_PROXY_TARGET=http://localhost:8000 npm run dev
```

## API (prefix `/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create user |
| POST | `/auth/login` | OAuth2 password → `{access_token}` |
| GET | `/auth/me` | Current user |
| GET | `/documents` | List documents |
| POST | `/documents` | Upload image |
| GET | `/documents/{id}` | Document metadata |
| GET | `/documents/{id}/file` | Image bytes (auth-checked) |
| DELETE | `/documents/{id}` | Delete document + file + boxes |
| GET | `/documents/{id}/boxes` | List boxes |
| PUT | `/documents/{id}/boxes` | Bulk replace boxes |
| POST | `/documents/{id}/ocr` | Run OCR engine (stub → no boxes in Phase 1) |

## Out of scope (Phase 1)

Real OCR engine, multi-page/PDF documents, reading-order/text export,
roles/sharing.
