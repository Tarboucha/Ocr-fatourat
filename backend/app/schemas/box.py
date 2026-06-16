from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BoxBase(BaseModel):
    x: float
    y: float
    w: float
    h: float
    text: str | None = None
    source: Literal["manual", "ocr"] = "manual"
    confidence: float | None = None
    order: int = 0


class BoxIn(BoxBase):
    """A box submitted by the client. `id` is optional and ignored on bulk save."""

    id: int | None = None


class BoxOut(BoxBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    created_at: datetime
    updated_at: datetime


class BoxBulkIn(BaseModel):
    boxes: list[BoxIn]
