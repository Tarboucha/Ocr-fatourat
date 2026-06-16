from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.documents import _get_owned_document
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Box, User
from app.schemas.box import BoxOut
from app.services.ocr import get_ocr_engine

router = APIRouter(prefix="/documents/{doc_id}/ocr", tags=["ocr"])


@router.post("", response_model=list[BoxOut])
async def run_ocr(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the configured OCR engine and persist detections as `source=ocr` boxes.

    Phase 1 uses StubOcrEngine, which returns [] — the path is fully wired but
    produces no boxes until a real engine is plugged in.
    """
    doc = await _get_owned_document(doc_id, user, db)

    engine = get_ocr_engine()
    detections = engine.detect(doc.stored_path)

    created = [
        Box(
            document_id=doc_id,
            x=d.x,
            y=d.y,
            w=d.w,
            h=d.h,
            text=d.text,
            source="ocr",
            confidence=d.confidence,
            order=i,
        )
        for i, d in enumerate(detections)
    ]
    if created:
        db.add_all(created)
        await db.commit()

    rows = await db.scalars(
        select(Box).where(Box.document_id == doc_id).order_by(Box.order, Box.id)
    )
    return list(rows)
