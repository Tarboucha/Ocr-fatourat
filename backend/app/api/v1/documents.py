import io
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Document, User
from app.schemas.document import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff"}


async def _get_owned_document(doc_id: int, user: User, db: AsyncSession) -> Document:
    doc = await db.get(Document, doc_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


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
    try:
        with Image.open(io.BytesIO(raw)) as img:
            width, height = img.size
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="File is not a valid image")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".bin"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as fh:
        fh.write(raw)

    doc = Document(
        owner_id=user.id,
        filename=file.filename or stored_name,
        stored_path=stored_path,
        mime_type=file.content_type,
        width=width,
        height=height,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _get_owned_document(doc_id, user, db)


@router.get("/{doc_id}/file")
async def get_document_file(
    doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    doc = await _get_owned_document(doc_id, user, db)
    if not os.path.exists(doc.stored_path):
        raise HTTPException(status_code=404, detail="File missing from storage")
    return FileResponse(doc.stored_path, media_type=doc.mime_type, filename=doc.filename)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    doc = await _get_owned_document(doc_id, user, db)
    path = doc.stored_path
    await db.delete(doc)  # cascades to boxes
    await db.commit()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
