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


@runtime_checkable
class OcrEngine(Protocol):
    """Pluggable OCR backend. Phase 1 ships only a stub; real engines
    (Tesseract, PaddleOCR, cloud APIs) implement this same interface later."""

    def detect(self, image_path: str) -> list[OcrBox]:
        ...
