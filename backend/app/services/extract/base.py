from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.invoice import InvoiceDocument
from app.services.ocr.base import OcrBox


@runtime_checkable
class Extractor(Protocol):
    """Turns a document's pages (images + optional OCR boxes) into a structured
    InvoiceDocument. Register implementations with @register_extractor so they
    are listable/selectable without any other code change.

    `needs_ocr` declares whether the extractor consumes the page's OCR boxes
    (heuristic) or works straight from the image (ppstructure, vlm)."""

    name: str
    description: str
    needs_ocr: bool
    languages: list[str]

    def extract(
        self,
        image_paths: list[str],
        ocr_boxes_by_page: list[list[OcrBox]],
    ) -> InvoiceDocument:
        ...
