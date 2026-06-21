"""Turn an uploaded file (PDF or image) into per-page PNGs on disk.

PDFs are rendered with PyMuPDF at a fixed DPI; images become a single page.
All boxes (manual + OCR) live in the pixel space of these PNGs, so the canvas
and any future OCR engine share one coordinate system."""

import io
import os
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image

# Render DPI for PDF pages. 150 is a good accuracy/size tradeoff for OCR.
PDF_RENDER_DPI = 150


@dataclass
class RenderedPage:
    page_number: int  # 1-based
    path: str
    width: int
    height: int


def rasterize(raw: bytes, mime_type: str, dest_dir: str) -> list[RenderedPage]:
    """Write page PNGs into dest_dir and return their metadata."""
    os.makedirs(dest_dir, exist_ok=True)
    if mime_type == "application/pdf":
        return _rasterize_pdf(raw, dest_dir)
    return _rasterize_image(raw, dest_dir)


def _rasterize_pdf(raw: bytes, dest_dir: str) -> list[RenderedPage]:
    pages: list[RenderedPage] = []
    with fitz.open(stream=raw, filetype="pdf") as pdf:
        for index, page in enumerate(pdf):
            pix = page.get_pixmap(dpi=PDF_RENDER_DPI)
            page_number = index + 1
            path = os.path.join(dest_dir, f"page-{page_number:04d}.png")
            pix.save(path)
            pages.append(
                RenderedPage(page_number=page_number, path=path, width=pix.width, height=pix.height)
            )
    return pages


def _rasterize_image(raw: bytes, dest_dir: str) -> list[RenderedPage]:
    with Image.open(io.BytesIO(raw)) as img:
        rgb = img.convert("RGB")
        width, height = rgb.size
        path = os.path.join(dest_dir, "page-0001.png")
        rgb.save(path, format="PNG")
    return [RenderedPage(page_number=1, path=path, width=width, height=height)]
