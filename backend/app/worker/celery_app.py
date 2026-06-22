from celery import Celery
from celery.signals import worker_process_init

from app.core.config import settings

# Broker only — no result backend. OcrJob rows in Postgres are the source of
# truth for status/results, so Celery's result store is unnecessary.
celery_app = Celery("ocr", broker=settings.REDIS_URL, include=["app.worker.tasks"])

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings.OCR_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.OCR_TASK_SOFT_TIME_LIMIT,
)


@worker_process_init.connect
def _warmup(**_kwargs):
    """Load the default pipeline's models once per worker process so the first
    real OCR request isn't a cold start. Best-effort."""
    from app.services.ocr import get_pipeline

    try:
        get_pipeline(settings.DEFAULT_OCR_PIPELINE)
    except Exception:  # noqa: BLE001 - warmup is optional
        pass
