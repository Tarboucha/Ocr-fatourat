from PIL import Image

from app.services.ocr.base import OcrBox
from app.services.ocr.registry import register_pipeline
from app.services.ocr.util import clamp_region


@register_pipeline
class TesseractPipeline:
    """Lightweight fallback using the Tesseract binary via pytesseract.
    Good on clean printed scans; weaker on complex layouts/handwriting."""

    name = "tesseract"
    description = "Tesseract — light & fast on clean printed text"
    supports_region = True
    languages = ["eng", "fra", "ara"]

    def __init__(self) -> None:
        import pytesseract  # noqa: F401  (ensure the dep is present)

        self._pt = pytesseract

    def detect(self, image_path: str) -> list[OcrBox]:
        img = Image.open(image_path).convert("RGB")
        data = self._pt.image_to_data(img, output_type=self._pt.Output.DICT)
        boxes: list[OcrBox] = []
        n = len(data["text"])
        for i in range(n):
            text = (data["text"][i] or "").strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:
                continue
            boxes.append(
                OcrBox(
                    x=float(data["left"][i]),
                    y=float(data["top"][i]),
                    w=float(data["width"][i]),
                    h=float(data["height"][i]),
                    text=text,
                    confidence=conf / 100.0,
                )
            )
        return boxes

    def recognize_region(self, image_path: str, x: float, y: float, w: float, h: float) -> OcrBox:
        img = Image.open(image_path).convert("RGB")
        x0, y0, x1, y1 = clamp_region(x, y, w, h, img.width, img.height)
        crop = img.crop((x0, y0, x1, y1))
        text = self._pt.image_to_string(crop).strip()
        return OcrBox(x=x, y=y, w=w, h=h, text=text, confidence=None)
