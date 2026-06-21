from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.documents import get_owned_page
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Box, User
from app.schemas.box import BoxBulkIn, BoxOut

router = APIRouter(prefix="/pages/{page_id}/boxes", tags=["boxes"])


@router.get("", response_model=list[BoxOut])
async def list_boxes(
    page_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await get_owned_page(page_id, user, db)
    rows = await db.scalars(
        select(Box).where(Box.page_id == page_id).order_by(Box.order, Box.id)
    )
    return list(rows)


@router.put("", response_model=list[BoxOut])
async def replace_boxes(
    page_id: int,
    payload: BoxBulkIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk replace: simplest model for a canvas editor that owns the full set."""
    await get_owned_page(page_id, user, db)
    await db.execute(delete(Box).where(Box.page_id == page_id))
    new_boxes = [
        Box(
            page_id=page_id,
            x=b.x,
            y=b.y,
            w=b.w,
            h=b.h,
            text=b.text,
            source=b.source,
            confidence=b.confidence,
            order=b.order,
        )
        for b in payload.boxes
    ]
    db.add_all(new_boxes)
    await db.commit()
    rows = await db.scalars(
        select(Box).where(Box.page_id == page_id).order_by(Box.order, Box.id)
    )
    return list(rows)
