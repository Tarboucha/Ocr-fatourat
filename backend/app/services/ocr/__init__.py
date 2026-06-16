from app.services.ocr.base import OcrBox, OcrEngine
from app.services.ocr.stub import StubOcrEngine

# Single switch point: swap this for a real engine (Tesseract/PaddleOCR/cloud) later.
_engine: OcrEngine = StubOcrEngine()


def get_ocr_engine() -> OcrEngine:
    return _engine


__all__ = ["OcrBox", "OcrEngine", "StubOcrEngine", "get_ocr_engine"]
