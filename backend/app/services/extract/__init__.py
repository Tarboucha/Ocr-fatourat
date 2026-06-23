"""Invoice extraction package. Importing it registers all extractors.

Module imports keep heavy deps lazy, so the lean API image can list/validate
extractors without the paddle/VLM stacks installed."""

from app.services.extract.base import Extractor
from app.services.extract.normalize import normalize_invoice
from app.services.extract.registry import (
    available_extractors,
    get_extractor,
    is_registered,
    register_extractor,
)

# Import side effects register each extractor.
from app.services.extract import heuristic  # noqa: F401,E402
from app.services.extract import ppstructure  # noqa: F401,E402
from app.services.extract import vlm  # noqa: F401,E402

__all__ = [
    "Extractor",
    "normalize_invoice",
    "available_extractors",
    "get_extractor",
    "is_registered",
    "register_extractor",
]
