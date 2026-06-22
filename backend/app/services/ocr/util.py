"""Shared helpers for OCR pipelines: polygon → axis-aligned box, and cropping."""

from typing import Sequence


def quad_to_aabb(points: Sequence[Sequence[float]]) -> tuple[float, float, float, float]:
    """Convert a quadrilateral [[x,y], ...] to an axis-aligned (x, y, w, h)."""
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    x0, y0 = min(xs), min(ys)
    return x0, y0, max(xs) - x0, max(ys) - y0


def clamp_region(
    x: float, y: float, w: float, h: float, img_w: int, img_h: int
) -> tuple[int, int, int, int]:
    """Clamp a region to image bounds and return integer pixel box."""
    x0 = max(0, int(round(x)))
    y0 = max(0, int(round(y)))
    x1 = min(img_w, int(round(x + w)))
    y1 = min(img_h, int(round(y + h)))
    return x0, y0, max(x0 + 1, x1), max(y0 + 1, y1)
