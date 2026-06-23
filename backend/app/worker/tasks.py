from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import get_sync_sessionmaker
from app.models import Box, Document, Extraction, OcrJob, Page
from app.services.ocr import get_pipeline
from app.services.ocr.base import OcrBox
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


# Extraction (esp. PP-StructureV3) is far heavier than OCR and its first run
# downloads a large model set, so it gets a generous limit of its own rather
# than the short OCR limit.
@celery_app.task(name="extract.document", time_limit=1800, soft_time_limit=1500)
def extract_document(extraction_id: int) -> None:
    from app.services.extract import get_extractor, normalize_invoice

    Session = get_sync_sessionmaker()
    with Session() as db:
        ext = db.get(Extraction, extraction_id)
        if ext is None:
            return
        doc = db.get(Document, ext.document_id)
        if doc is None:
            ext.status = "failed"
            ext.error = "Document not found"
            ext.finished_at = _now()
            db.commit()
            return

        ext.status = "processing"
        ext.started_at = _now()
        db.commit()

        try:
            extractor = get_extractor(ext.extractor)
            pages = db.scalars(
                select(Page).where(Page.document_id == doc.id).order_by(Page.page_number)
            ).all()
            image_paths = [p.stored_path for p in pages]

            boxes_by_page: list[list[OcrBox]] = []
            if extractor.needs_ocr:
                for p in pages:
                    rows = db.scalars(
                        select(Box)
                        .where(Box.page_id == p.id, Box.source == "ocr")
                        .order_by(Box.order, Box.id)
                    ).all()
                    boxes_by_page.append(
                        [OcrBox(x=b.x, y=b.y, w=b.w, h=b.h, text=b.text or "",
                                confidence=b.confidence, id=b.id) for b in rows]
                    )
                if not any(boxes_by_page):
                    raise RuntimeError("No OCR results found — run OCR on the pages first")
            else:
                boxes_by_page = [[] for _ in pages]

            invoice = normalize_invoice(extractor.extract(image_paths, boxes_by_page))

            ext.data = invoice.model_dump()
            ext.schema_version = invoice.schema_version
            ext.needs_review = invoice.validation.needs_review
            ext.status = "done"
            ext.finished_at = _now()
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            ext = db.get(Extraction, extraction_id)
            if ext is not None:
                ext.status = "failed"
                ext.error = str(exc)[:2000]
                ext.finished_at = _now()
                db.commit()
