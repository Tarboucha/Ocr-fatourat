from __future__ import annotations

from PIL import Image

from app.services.ocr.base import OcrBox
from app.services.ocr.registry import register_pipeline
from app.services.ocr.util import clamp_region, quad_to_aabb


@register_pipeline
class PaddleOcrPipeline:
    """Native PaddleOCR (PP-OCR det+rec). Heavier than RapidOCR (pulls
    paddlepaddle) but useful to A/B against rapidocr and to access the latest
    PaddleOCR models. Heavy imports are deferred to instantiation; the module
    only registers (see services/ocr/__init__.py for the optional-import guard)."""

    name = "paddle"
    description = "PaddleOCR (native PP-OCR) — heavier, latest models"
    supports_region = True
    languages = ["en", "fr", "ar", "ch"]

    def __init__(self) -> None:
        from paddleocr import PaddleOCR

        self._engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    def _run(self, image) -> list[OcrBox]:
        result = self._engine.ocr(image, cls=True)
        boxes: list[OcrBox] = []
        # PaddleOCR returns [[ [quad, (text, score)], ... ]] (per-image list).
        for page in result or []:
            for line in page or []:
                quad, (text, score) = line
                x, y, w, h = quad_to_aabb(quad)
                boxes.append(
                    OcrBox(
                        x=x, y=y, w=w, h=h, text=text,
                        confidence=float(score) if score is not None else None,
                    )
                )
        return boxes

    def detect(self, image_path: str) -> list[OcrBox]:
        import numpy as np

        image = np.array(Image.open(image_path).convert("RGB"))
        return self._run(image)

    def recognize_region(self, image_path: str, x: float, y: float, w: float, h: float) -> OcrBox:
        import numpy as np

        img = Image.open(image_path).convert("RGB")
        x0, y0, x1, y1 = clamp_region(x, y, w, h, img.width, img.height)
        crop = np.array(img.crop((x0, y0, x1, y1)))
        found = self._run(crop)
        text = " ".join(b.text for b in found).strip()
        confs = [b.confidence for b in found if b.confidence is not None]
        conf = min(confs) if confs else None
        return OcrBox(x=x, y=y, w=w, h=h, text=text, confidence=conf)
