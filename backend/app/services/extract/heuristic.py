"""Heuristic table-structure recognition over OCR boxes.

Groups boxes into rows, finds the line-item header to derive column bands, then
assigns tokens to columns to build line items. Header fields (vendor, number,
date, totals) are found by keyword + regex. Transparent and dependency-free;
best on regular templates. Designed for FR/EN Tunisian invoices."""

from __future__ import annotations

import re

from app.schemas.invoice import ExtractedField, InvoiceDocument, LineItem
from app.services.extract.registry import register_extractor
from app.services.ocr.base import OcrBox

# Column header keywords (lowercased, FR + EN).
_COLS = {
    "description": ["désignation", "designation", "description", "libellé", "libelle", "article", "produit"],
    "quantity": ["qté", "qte", "quantité", "quantite", "quantity", "qty"],
    "unit_price": ["prix unitaire", "p.u", "p u", "pu", "unit price", "prix u"],
    "line_total": ["montant", "total", "prix total", "amount"],
}
_DATE_RE = re.compile(r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
_NUM_RE = re.compile(r"\d")


def _center_y(b: OcrBox) -> float:
    return b.y + b.h / 2


def _center_x(b: OcrBox) -> float:
    return b.x + b.w / 2


def _group_rows(boxes: list[OcrBox]) -> list[list[OcrBox]]:
    """Cluster boxes into visual rows by vertical proximity."""
    rows: list[list[OcrBox]] = []
    for b in sorted(boxes, key=_center_y):
        placed = False
        for row in rows:
            ref = row[0]
            if abs(_center_y(b) - _center_y(ref)) <= max(ref.h, b.h) * 0.6:
                row.append(b)
                placed = True
                break
        if not placed:
            rows.append([b])
    for row in rows:
        row.sort(key=_center_x)
    return rows


def _field(text: str, boxes: list[OcrBox]) -> ExtractedField:
    confs = [b.confidence for b in boxes if b.confidence is not None]
    ids = [b.id for b in boxes if b.id is not None]
    return ExtractedField(
        value=text or None,
        raw_text=text or None,
        confidence=min(confs) if confs else None,
        box_ids=ids,
    )


def _find_header(rows: list[list[OcrBox]]) -> tuple[int, dict[str, float]] | None:
    for i, row in enumerate(rows):
        centers: dict[str, float] = {}
        for col, kws in _COLS.items():
            for b in row:
                t = b.text.lower().strip()
                if any(kw in t for kw in kws):
                    centers[col] = _center_x(b)
                    break
        if len(centers) >= 2:
            return i, centers
    return None


def _assign_column(x: float, centers: dict[str, float]) -> str | None:
    if not centers:
        return None
    return min(centers, key=lambda c: abs(centers[c] - x))


class HeuristicExtractor:
    name = "heuristic"
    description = "Clusters OCR boxes into rows/columns (FR/EN). Light, transparent."
    needs_ocr = True
    languages = ["fr", "en"]

    def extract(
        self,
        image_paths: list[str],
        ocr_boxes_by_page: list[list[OcrBox]],
    ) -> InvoiceDocument:
        doc = InvoiceDocument()
        all_text_lines: list[str] = []

        for boxes in ocr_boxes_by_page:
            if not boxes:
                continue
            rows = _group_rows(boxes)
            for row in rows:
                all_text_lines.append(" ".join(b.text for b in row))

            header = _find_header(rows)
            if header is None:
                continue
            header_idx, centers = header
            for row in rows[header_idx + 1 :]:
                col_boxes: dict[str, list[OcrBox]] = {c: [] for c in centers}
                for b in row:
                    col = _assign_column(_center_x(b), centers)
                    if col:
                        col_boxes[col].append(b)
                amount_text = " ".join(b.text for b in col_boxes.get("line_total", []))
                if "line_total" not in centers or not _NUM_RE.search(amount_text):
                    continue  # not a line-item row
                item = LineItem(
                    description=_field(
                        " ".join(b.text for b in col_boxes.get("description", [])),
                        col_boxes.get("description", []),
                    ),
                    quantity=_field(
                        " ".join(b.text for b in col_boxes.get("quantity", [])),
                        col_boxes.get("quantity", []),
                    ),
                    unit_price=_field(
                        " ".join(b.text for b in col_boxes.get("unit_price", [])),
                        col_boxes.get("unit_price", []),
                    ),
                    line_total=_field(amount_text, col_boxes.get("line_total", [])),
                )
                doc.line_items.append(item)

        self._fill_header_fields(doc, ocr_boxes_by_page, all_text_lines)
        return doc

    def _fill_header_fields(self, doc, ocr_boxes_by_page, lines: list[str]) -> None:
        full = "\n".join(lines)
        # vendor: first non-empty line of page 1 (rough).
        if ocr_boxes_by_page and ocr_boxes_by_page[0]:
            first_rows = _group_rows(ocr_boxes_by_page[0])
            if first_rows:
                top = first_rows[0]
                doc.vendor = _field(" ".join(b.text for b in top), top)

        m = re.search(r"(?:facture|invoice|n[°o.]+)\s*[:#]?\s*([A-Za-z0-9\-/]+)", full, re.I)
        if m:
            doc.invoice_number = ExtractedField(value=m.group(1), raw_text=m.group(0))
        d = _DATE_RE.search(full)
        if d:
            doc.date = ExtractedField(value=d.group(1), raw_text=d.group(1))
        if re.search(r"\b(tnd|dt|dinar)\b", full, re.I):
            doc.currency = ExtractedField(value="TND")
        elif "€" in full:
            doc.currency = ExtractedField(value="EUR")

        # totals: take the numeric on lines that mention the label.
        for line in lines:
            low = line.lower()
            if "total" in low and "ttc" in low:
                doc.total = _amount_field(line)
            elif ("sous-total" in low or "total ht" in low or "subtotal" in low) and doc.subtotal.value is None:
                doc.subtotal = _amount_field(line)
            elif "tva" in low or "tax" in low:
                doc.tax = _amount_field(line)
            elif "total" in low and doc.total.value is None:
                doc.total = _amount_field(line)


def _amount_field(line: str) -> ExtractedField:
    nums = re.findall(r"[0-9][0-9.,\s]*[0-9]|[0-9]", line)
    raw = nums[-1].strip() if nums else None
    return ExtractedField(value=raw, raw_text=raw)


register_extractor(HeuristicExtractor)
