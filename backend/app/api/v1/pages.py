import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.documents import get_owned_page
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("/{page_id}/file")
async def get_page_file(
    page_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    page = await get_owned_page(page_id, user, db)
    if not os.path.exists(page.stored_path):
        raise HTTPException(status_code=404, detail="Page image missing from storage")
    return FileResponse(page.stored_path, media_type="image/png")
