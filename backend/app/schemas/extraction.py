from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ExtractorInfoOut(BaseModel):
    name: str
    description: str
    needs_ocr: bool
    languages: list[str]


class RunExtractIn(BaseModel):
    extractor: str | None = None


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    extractor: str
    status: str
    error: str | None
    schema_version: str | None
    needs_review: bool
    data: Any | None
    created_at: datetime
