import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Document, Page, User
from app.schemas.document import DocumentOut, PageOut
from app.services.rasterize import rasterize

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_MIME = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

_EXT_BY_MIME = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}


async def _get_owned_document(doc_id: int, user: User, db: AsyncSession) -> Document:
    doc = await db.get(Document, doc_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


async def get_owned_page(page_id: int, user: User, db: AsyncSession) -> Page:
    page = await db.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    doc = await db.get(Document, page.document_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = await db.scalars(
        select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())
    )
    return list(rows)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in _ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    raw = await file.read()

    storage_id = uuid.uuid4().hex
    doc_dir = os.path.join(settings.UPLOAD_DIR, storage_id)
    os.makedirs(doc_dir, exist_ok=True)

    # Persist the original upload, then rasterize into per-page PNGs.
    ext = _EXT_BY_MIME.get(file.content_type, ".bin")
    original_path = os.path.join(doc_dir, f"original{ext}")
    with open(original_path, "wb") as fh:
        fh.write(raw)

    try:
        rendered = rasterize(raw, file.content_type, doc_dir)
    except Exception as exc:  # noqa: BLE001 - surface a clean 400 for bad files
        shutil.rmtree(doc_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}") from exc

    if not rendered:
        shutil.rmtree(doc_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="File contained no pages")

    doc = Document(
        owner_id=user.id,
        filename=file.filename or f"upload{ext}",
        mime_type=file.content_type,
        original_path=original_path,
        page_count=len(rendered),
        status="uploaded",
    )
    doc.pages = [
        Page(
            page_number=r.page_number,
            stored_path=r.path,
            width=r.width,
            height=r.height,
        )
        for r in rendered
    ]
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _get_owned_document(doc_id, user, db)


@router.get("/{doc_id}/pages", response_model=list[PageOut])
async def list_pages(
    doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _get_owned_document(doc_id, user, db)
    rows = await db.scalars(
        select(Page).where(Page.document_id == doc_id).order_by(Page.page_number)
    )
    return list(rows)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    doc = await _get_owned_document(doc_id, user, db)
    # All page PNGs and the original live under one per-document directory.
    doc_dir = os.path.dirname(doc.original_path)
    await db.delete(doc)  # cascades to pages -> boxes
    await db.commit()
    if doc_dir and os.path.isdir(doc_dir):
        shutil.rmtree(doc_dir, ignore_errors=True)
