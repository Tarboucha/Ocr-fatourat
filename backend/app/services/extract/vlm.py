"""VLM extractor: sends each page image to an OpenAI-compatible vision chat
endpoint and asks for the invoice JSON directly. Provider-agnostic via config
(EXTRACT_VLM_BASE_URL / _MODEL / _API_KEY) — works with OpenAI, OpenRouter, or a
local OpenAI-compatible server. Output still flows through normalize() for the
same validation as every other extractor (catches hallucinated arithmetic)."""

from __future__ import annotations

import base64
import json

from app.core.config import settings
from app.schemas.invoice import ExtractedField, InvoiceDocument, LineItem
from app.services.extract.registry import register_extractor

_PROMPT = """You are an invoice parser. Read the invoice image and return ONLY a JSON
object (no prose, no markdown) with this exact shape:
{
  "vendor": str, "invoice_number": str, "date": str, "due_date": str, "currency": str,
  "line_items": [{"description": str, "quantity": number, "unit_price": number, "line_total": number}],
  "subtotal": number, "tax": number, "total": number, "amount_due": number
}
Use null for anything not present. Use plain numbers (no currency symbols, dot as decimal)."""


def _f(v) -> ExtractedField:
    return ExtractedField(value=v if v != "" else None, raw_text=str(v) if v is not None else None)


class VlmExtractor:
    name = "vlm"
    description = "Vision LLM → JSON (config-driven provider). Best for messy layouts."
    needs_ocr = False
    languages = ["fr", "en", "ar"]

    def _b64(self, path: str) -> str:
        with open(path, "rb") as fh:
            return base64.b64encode(fh.read()).decode()

    def extract(self, image_paths, ocr_boxes_by_page) -> InvoiceDocument:
        if not settings.EXTRACT_VLM_API_KEY:
            raise RuntimeError("VLM extractor needs EXTRACT_VLM_API_KEY to be set")
        import httpx

        # Use the first page (multi-page stitching is out of scope for v1).
        data_url = f"data:image/png;base64,{self._b64(image_paths[0])}"
        payload = {
            "model": settings.EXTRACT_VLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "temperature": 0,
        }
        resp = httpx.post(
            f"{settings.EXTRACT_VLM_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.EXTRACT_VLM_API_KEY}"},
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        raw = json.loads(_strip_fence(content))

        doc = InvoiceDocument()
        doc.vendor = _f(raw.get("vendor"))
        doc.invoice_number = _f(raw.get("invoice_number"))
        doc.date = _f(raw.get("date"))
        doc.due_date = _f(raw.get("due_date"))
        doc.currency = _f(raw.get("currency"))
        doc.subtotal = _f(raw.get("subtotal"))
        doc.tax = _f(raw.get("tax"))
        doc.total = _f(raw.get("total"))
        doc.amount_due = _f(raw.get("amount_due"))
        for li in raw.get("line_items") or []:
            doc.line_items.append(
                LineItem(
                    description=_f(li.get("description")),
                    quantity=_f(li.get("quantity")),
                    unit_price=_f(li.get("unit_price")),
                    line_total=_f(li.get("line_total")),
                )
            )
        return doc


def _strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    return s.strip()


register_extractor(VlmExtractor)
