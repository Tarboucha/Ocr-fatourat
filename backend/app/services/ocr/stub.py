from app.services.ocr.base import OcrBox
from app.services.ocr.registry import register_pipeline


@register_pipeline
class StubPipeline:
    """Returns no detections. Useful as a safe default and for fast CI tests —
    exercises the full enqueue → worker → status path with no ML deps."""

    name = "stub"
    description = "No-op pipeline (returns nothing) — for testing the flow"
    supports_region = True
    languages = ["en"]

    def detect(self, image_path: str) -> list[OcrBox]:
        return []

    def recognize_region(self, image_path: str, x: float, y: float, w: float, h: float) -> OcrBox:
        return OcrBox(x=x, y=y, w=w, h=h, text="", confidence=None)
