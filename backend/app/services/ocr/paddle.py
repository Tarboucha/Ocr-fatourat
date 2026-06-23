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
    only registers.

    Targets PaddleOCR 3.x: the `.predict()` API returns per-image dicts with
    `rec_texts` / `rec_scores` / `rec_polys`. `enable_mkldnn=False` avoids a
    PIR/oneDNN runtime bug on slim CPU builds."""

    name = "paddle"
    description = "PaddleOCR (native PP-OCR 3.x) — heavier, latest models"
    supports_region = True
    languages = ["en", "fr", "ar", "ch"]

    def __init__(self) -> None:
        from paddleocr import PaddleOCR

        self._engine = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )

    def _run(self, image) -> list[OcrBox]:
        boxes: list[OcrBox] = []
        for r in self._engine.predict(image):
            texts = r.get("rec_texts") or []
            scores = r.get("rec_scores") or []
            polys = r.get("rec_polys")
            if polys is None:
                polys = r.get("dt_polys") or []
            for i, text in enumerate(texts):
                if i >= len(polys):
                    break
                x, y, w, h = quad_to_aabb(polys[i])
                score = scores[i] if i < len(scores) else None
                boxes.append(
                    OcrBox(x=x, y=y, w=w, h=h, text=text,
                           confidence=float(score) if score is not None else None)
                )
        return boxes

    def detect(self, image_path: str) -> list[OcrBox]:
        import numpy as np

        return self._run(np.array(Image.open(image_path).convert("RGB")))

    def recognize_region(self, image_path: str, x: float, y: float, w: float, h: float) -> OcrBox:
        import numpy as np

        img = Image.open(image_path).convert("RGB")
        x0, y0, x1, y1 = clamp_region(x, y, w, h, img.width, img.height)
        found = self._run(np.array(img.crop((x0, y0, x1, y1))))
        text = " ".join(b.text for b in found).strip()
        confs = [b.confidence for b in found if b.confidence is not None]
        return OcrBox(x=x, y=y, w=w, h=h, text=text, confidence=min(confs) if confs else None)
