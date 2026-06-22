from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.documents import get_owned_page
from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import OcrJob, User
from app.schemas.ocr import OcrJobOut, PipelineInfoOut, RunOcrIn, RunRegionIn
from app.services.ocr import available_pipelines, is_registered
from app.worker.celery_app import celery_app

router = APIRouter(tags=["ocr"])

_ACTIVE = ("queued", "processing")


def _resolve_pipeline(name: str | None) -> str:
    chosen = name or settings.DEFAULT_OCR_PIPELINE
    if not is_registered(chosen):
        raise HTTPException(status_code=400, detail=f"Unknown OCR pipeline: {chosen}")
    return chosen


@router.get("/ocr/pipelines", response_model=list[PipelineInfoOut])
async def list_pipelines(_user: User = Depends(get_current_user)):
    return available_pipelines()


@router.post("/pages/{page_id}/ocr", response_model=OcrJobOut, status_code=status.HTTP_202_ACCEPTED)
async def run_page_ocr(
    page_id: int,
    payload: RunOcrIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = await get_owned_page(page_id, user, db)
    pipeline = _resolve_pipeline(payload.pipeline)

    # Guard: refuse a duplicate page run for the same pipeline already in flight.
    active = await db.scalar(
        select(OcrJob).where(
            OcrJob.page_id == page.id,
            OcrJob.kind == "page",
            OcrJob.pipeline == pipeline,
            OcrJob.status.in_(_ACTIVE),
        )
    )
    if active is not None:
        raise HTTPException(status_code=409, detail="An OCR run is already in progress")

    job = OcrJob(page_id=page.id, kind="page", pipeline=pipeline, status="queued")
    db.add(job)
    page.ocr_status = "queued"
    await db.commit()
    await db.refresh(job)

    celery_app.send_task("ocr.page", args=[job.id])
    return job


@router.post(
    "/pages/{page_id}/ocr/region",
    response_model=OcrJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_region_ocr(
    page_id: int,
    payload: RunRegionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = await get_owned_page(page_id, user, db)
    pipeline = _resolve_pipeline(payload.pipeline)

    info = next((p for p in available_pipelines() if p.name == pipeline), None)
    if info is not None and not info.supports_region:
        raise HTTPException(
            status_code=400, detail=f"Pipeline '{pipeline}' does not support region OCR"
        )

    job = OcrJob(
        page_id=page.id,
        kind="region",
        pipeline=pipeline,
        status="queued",
        x=payload.x,
        y=payload.y,
        w=payload.w,
        h=payload.h,
        box_id=payload.box_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    celery_app.send_task("ocr.region", args=[job.id])
    return job


@router.get("/ocr/jobs/{job_id}", response_model=OcrJobOut)
async def get_job(
    job_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    job = await db.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    # Ownership: the job's page must belong to the user (raises 404 otherwise).
    await get_owned_page(job.page_id, user, db)
    return job
