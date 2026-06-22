"""OCR pipeline package.

Importing this package registers all available pipelines. `stub` and `rapidocr`
are always registered (their heavy deps load lazily on first use). `tesseract`
and `paddle` self-register too, but are only *usable* if their optional deps are
installed — instantiation (get_pipeline) will raise otherwise.
"""

from app.services.ocr.base import OcrBox, OcrPipeline
from app.services.ocr.registry import (
    available_pipelines,
    get_pipeline,
    is_registered,
    register_pipeline,
)

# Import side effects register each pipeline. Modules avoid heavy top-level
# imports, so this is safe even in the lean API image.
from app.services.ocr import stub  # noqa: F401,E402
from app.services.ocr import rapidocr  # noqa: F401,E402
from app.services.ocr import tesseract  # noqa: F401,E402
from app.services.ocr import paddle  # noqa: F401,E402

__all__ = [
    "OcrBox",
    "OcrPipeline",
    "register_pipeline",
    "available_pipelines",
    "get_pipeline",
    "is_registered",
]
