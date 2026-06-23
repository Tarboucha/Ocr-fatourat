import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.documents import _get_owned_document
from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Extraction, User
from app.schemas.extraction import ExtractionOut, ExtractorInfoOut, RunExtractIn
from app.services.extract import available_extractors, is_registered
from app.worker.celery_app import celery_app

router = APIRouter(tags=["extract"])


async def _get_owned_extraction(extraction_id: int, user: User, db: AsyncSession) -> Extraction:
    ext = await db.get(Extraction, extraction_id)
    if ext is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    await _get_owned_document(ext.document_id, user, db)  # ownership check (404 otherwise)
    return ext


@router.get("/extract/extractors", response_model=list[ExtractorInfoOut])
async def list_extractors(_user: User = Depends(get_current_user)):
    return available_extractors()


@router.post(
    "/documents/{doc_id}/extract",
    response_model=ExtractionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_extract(
    doc_id: int,
    payload: RunExtractIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_document(doc_id, user, db)
    extractor = payload.extractor or settings.DEFAULT_EXTRACTOR
    if not is_registered(extractor):
        raise HTTPException(status_code=400, detail=f"Unknown extractor: {extractor}")

    ext = Extraction(document_id=doc_id, extractor=extractor, status="queued")
    db.add(ext)
    await db.commit()
    await db.refresh(ext)

    celery_app.send_task("extract.document", args=[ext.id])
    return ext


@router.get("/documents/{doc_id}/extractions", response_model=list[ExtractionOut])
async def list_extractions(
    doc_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _get_owned_document(doc_id, user, db)
    rows = await db.scalars(
        select(Extraction)
        .where(Extraction.document_id == doc_id)
        .order_by(Extraction.created_at.desc())
    )
    return list(rows)


@router.get("/extractions/{extraction_id}", response_model=ExtractionOut)
async def get_extraction(
    extraction_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _get_owned_extraction(extraction_id, user, db)


@router.get("/extractions/{extraction_id}/export")
async def export_extraction(
    extraction_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    ext = await _get_owned_extraction(extraction_id, user, db)
    if ext.data is None:
        raise HTTPException(status_code=409, detail="Extraction has no data yet")
    body = json.dumps(ext.data, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="invoice-{ext.document_id}-{ext.extractor}.json"'
        },
    )
