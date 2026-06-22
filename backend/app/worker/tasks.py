from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import get_sync_sessionmaker
from app.models import Box, OcrJob, Page
from app.services.ocr import get_pipeline
from app.worker.celery_app import celery_app


def _now() -> datetime:
    return datetime.now(timezone.utc)


@celery_app.task(name="ocr.page")
def ocr_page(job_id: int) -> None:
    Session = get_sync_sessionmaker()
    with Session() as db:
        job = db.get(OcrJob, job_id)
        if job is None:
            return
        page = db.get(Page, job.page_id)
        if page is None:
            _fail(db, job, None, "Page not found")
            return

        job.status = "processing"
        job.started_at = _now()
        page.ocr_status = "processing"
        db.commit()

        try:
            pipeline = get_pipeline(job.pipeline)
            detections = pipeline.detect(page.stored_path)

            # Scoped replace: drop only boxes from prior runs of THIS pipeline
            # on this page (keep manual boxes and other pipelines' boxes).
            prior_ids = db.scalars(
                select(OcrJob.id).where(
                    OcrJob.page_id == page.id, OcrJob.pipeline == job.pipeline
                )
            ).all()
            if prior_ids:
                for b in db.scalars(
                    select(Box).where(
                        Box.page_id == page.id, Box.ocr_job_id.in_(prior_ids)
                    )
                ).all():
                    db.delete(b)

            for i, d in enumerate(detections):
                db.add(
                    Box(
                        page_id=page.id,
                        x=d.x, y=d.y, w=d.w, h=d.h,
                        text=d.text,
                        source="ocr",
                        confidence=d.confidence,
                        order=i,
                        ocr_job_id=job.id,
                    )
                )

            job.box_count = len(detections)
            job.status = "done"
            job.finished_at = _now()
            page.ocr_status = "done"
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            _fail(db, job, page, str(exc))


@celery_app.task(name="ocr.region")
def ocr_region(job_id: int) -> None:
    Session = get_sync_sessionmaker()
    with Session() as db:
        job = db.get(OcrJob, job_id)
        if job is None:
            return
        page = db.get(Page, job.page_id)
        if page is None:
            _fail(db, job, None, "Page not found")
            return

        job.status = "processing"
        job.started_at = _now()
        db.commit()

        try:
            pipeline = get_pipeline(job.pipeline)
            res = pipeline.recognize_region(page.stored_path, job.x, job.y, job.w, job.h)

            box = db.get(Box, job.box_id) if job.box_id else None
            if box is not None:
                box.text = res.text
                box.source = "ocr"
                box.confidence = res.confidence
                box.ocr_job_id = job.id
            else:
                box = Box(
                    page_id=page.id,
                    x=res.x, y=res.y, w=res.w, h=res.h,
                    text=res.text,
                    source="ocr",
                    confidence=res.confidence,
                    order=0,
                    ocr_job_id=job.id,
                )
                db.add(box)
                db.flush()
                job.box_id = box.id

            job.result_text = res.text
            job.result_confidence = res.confidence
            job.status = "done"
            job.finished_at = _now()
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            _fail(db, job, page, str(exc))


def _fail(db, job: OcrJob, page: Page | None, message: str) -> None:
    job.status = "failed"
    job.error = message[:2000]
    job.finished_at = _now()
    if page is not None and job.kind == "page":
        page.ocr_status = "failed"
    db.commit()
