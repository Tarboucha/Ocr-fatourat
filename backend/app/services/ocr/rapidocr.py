from __future__ import annotations

from PIL import Image

from app.services.ocr.base import OcrBox
from app.services.ocr.registry import register_pipeline
from app.services.ocr.util import clamp_region, quad_to_aabb


@register_pipeline
class RapidOcrPipeline:
    """Default pipeline. Runs PaddleOCR's PP-OCR detection + recognition models
    on ONNXRuntime via RapidOCR — same model family as PaddleOCR, far lighter
    install. Output boxes are in page-pixel coordinates.

    Heavy imports (rapidocr_onnxruntime, numpy) are deferred to instantiation so
    this module is importable in the lean API image just for registration."""

    name = "rapidocr"
    description = "RapidOCR (PP-OCR det+rec on ONNXRuntime) — fast, light, multilingual"
    supports_region = True
    languages = ["en", "fr", "ar", "ch"]

    def __init__(self) -> None:
        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR()

    def _run(self, image) -> list[OcrBox]:
        result, _ = self._engine(image)
        if not result:
            return []
        boxes: list[OcrBox] = []
        for quad, text, score in result:
            x, y, w, h = quad_to_aabb(quad)
            boxes.append(
                OcrBox(x=x, y=y, w=w, h=h, text=text, confidence=float(score) if score else None)
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
