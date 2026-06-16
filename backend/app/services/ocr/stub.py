from app.services.ocr.base import OcrBox


class StubOcrEngine:
    """Phase 1 placeholder. Returns no detections; the request/response and
    persistence path is fully wired so swapping in a real engine is trivial."""

    def detect(self, image_path: str) -> list[OcrBox]:
        return []
