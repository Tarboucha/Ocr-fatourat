"""PaddleOCR PP-StructureV3 table extractor (PaddleOCR 3.x). Recovers table
grids from the page image, then maps columns to invoice fields.

Optional: needs the `[paddle]` extra (paddleocr + paddlepaddle + paddlex[ocr]).
Heavy imports are deferred so the module is import-safe for listing."""

from __future__ import annotations

from html.parser import HTMLParser

from app.schemas.invoice import ExtractedField, InvoiceDocument, LineItem
from app.services.extract.registry import register_extractor

_COLS = {
    "description": ["désignation", "designation", "description", "libellé", "libelle", "article"],
    "quantity": ["qté", "qte", "quantité", "quantite", "quantity", "qty"],
    "unit_price": ["prix unitaire", "p.u", "pu", "unit price"],
    "line_total": ["montant", "total", "amount"],
}


class _TableParser(HTMLParser):
    """Extract rows of cell-text from a PP-Structure HTML <table>."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def _map_columns(header: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, cell in enumerate(header):
        t = cell.lower().strip()
        for col, kws in _COLS.items():
            if col not in mapping and any(kw in t for kw in kws):
                mapping[col] = idx
    return mapping


def _tables_from_result(r) -> list[str]:
    """Return the list of table HTML strings from a PPStructureV3 result."""
    htmls: list[str] = []
    table_list = r.get("table_res_list") if hasattr(r, "get") else None
    for t in table_list or []:
        html = t.get("pred_html") or t.get("html")
        if html:
            htmls.append(html)
    return htmls


class PpStructureExtractor:
    name = "ppstructure"
    description = "PaddleOCR PP-StructureV3 table recognition (needs the paddle extra)"
    needs_ocr = False
    languages = ["fr", "en", "ar"]

    def __init__(self) -> None:
        from paddleocr import PPStructureV3

        self._engine = PPStructureV3(
            # Force the lighter mobile OCR models (default pulls the large
            # PP-OCRv5_server_* models — slower to download and run on CPU).
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            use_seal_recognition=False,
            use_formula_recognition=False,
            use_chart_recognition=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )

    def extract(self, image_paths, ocr_boxes_by_page) -> InvoiceDocument:
        import numpy as np
        from PIL import Image

        doc = InvoiceDocument()
        for path in image_paths:
            image = np.array(Image.open(path).convert("RGB"))
            for r in self._engine.predict(image):
                for html in _tables_from_result(r):
                    parser = _TableParser()
                    parser.feed(html)
                    rows = [row for row in parser.rows if any(c for c in row)]
                    if len(rows) < 2:
                        continue
                    cols = _map_columns(rows[0])
                    if "line_total" not in cols:
                        continue
                    for row in rows[1:]:
                        def cell(col: str) -> ExtractedField:
                            i = cols.get(col)
                            v = row[i] if i is not None and i < len(row) else None
                            return ExtractedField(value=v or None, raw_text=v or None)

                        amount = cell("line_total")
                        if not amount.value:
                            continue
                        doc.line_items.append(
                            LineItem(
                                description=cell("description"),
                                quantity=cell("quantity"),
                                unit_price=cell("unit_price"),
                                line_total=amount,
                            )
                        )
        return doc


register_extractor(PpStructureExtractor)
