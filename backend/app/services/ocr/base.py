from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class OcrBox:
    """A detected text region in image-pixel coordinates."""

    x: float
    y: float
    w: float
    h: float
    text: str
    confidence: float | None = None
    # Set when the box is loaded from a persisted Box row, so extractors can
    # record provenance (which boxes a field came from). OCR engines leave None.
    id: int | None = None


@runtime_checkable
class OcrPipeline(Protocol):
    """A pluggable OCR backend. Implementations declare capability metadata and
    implement detection + region recognition. Adding a pipeline = write a class
    that satisfies this Protocol and decorate it with @register_pipeline.

    A pipeline may be arbitrarily multi-stage internally (deskew → detect →
    recognize → post-process); the registry only cares about this interface.
    """

    # Capability metadata (class attributes).
    name: str
    description: str
    supports_region: bool
    languages: list[str]

    def detect(self, image_path: str) -> list[OcrBox]:
        """Full-page OCR: return all detected text regions."""
        ...

    def recognize_region(self, image_path: str, x: float, y: float, w: float, h: float) -> OcrBox:
        """OCR a single region (crop) and return its text in page coordinates."""
        ...
