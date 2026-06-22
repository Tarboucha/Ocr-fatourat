from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OcrJob(Base):
    """Authoritative record of one OCR run (full-page or region), produced
    asynchronously by the Celery worker. Status is read from here (not Celery's
    result backend), and ownership is enforced via page → document → owner."""

    __tablename__ = "ocr_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # page | region
    pipeline: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    error: Mapped[str | None] = mapped_column(String, nullable=True)

    # region jobs only
    x: Mapped[float | None] = mapped_column(Float, nullable=True)
    y: Mapped[float | None] = mapped_column(Float, nullable=True)
    w: Mapped[float | None] = mapped_column(Float, nullable=True)
    h: Mapped[float | None] = mapped_column(Float, nullable=True)
    box_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # target box for region
    result_text: Mapped[str | None] = mapped_column(String, nullable=True)
    result_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # page jobs: number of boxes produced
    box_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    page: Mapped["Page"] = relationship()  # noqa: F821
