from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Page(Base):
    """A single rasterized page image belonging to a Document.

    `stored_path` points at a PNG; `width`/`height` are that PNG's pixel size,
    which is the coordinate space all boxes (manual + OCR) live in."""

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    # Denormalized mirror of the latest *page* OCR job for cheap badges.
    # OcrJob remains authoritative. idle|queued|processing|done|failed
    ocr_status: Mapped[str] = mapped_column(String(16), default="idle", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="pages")  # noqa: F821
    boxes: Mapped[list["Box"]] = relationship(  # noqa: F821
        back_populates="page", cascade="all, delete-orphan"
    )
