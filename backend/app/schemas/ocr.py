from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PipelineInfoOut(BaseModel):
    name: str
    description: str
    supports_region: bool
    languages: list[str]


class RunOcrIn(BaseModel):
    pipeline: str | None = None


class RunRegionIn(BaseModel):
    x: float
    y: float
    w: float
    h: float
    box_id: int | None = None
    pipeline: str | None = None


class OcrJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    page_id: int
    kind: str
    pipeline: str
    status: str
    error: str | None
    box_id: int | None
    result_text: str | None
    result_confidence: float | None
    box_count: int | None
    created_at: datetime
