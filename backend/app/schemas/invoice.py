"""The canonical structured-invoice schema. Every extractor returns exactly this
type, so the API / DB / UI never branch on which engine produced it."""

from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


class ExtractedField(BaseModel):
    value: Any = None
    confidence: float | None = None
    raw_text: str | None = None
    # Provenance: ids of the OCR/manual boxes this value came from (canvas link).
    box_ids: list[int] = Field(default_factory=list)


class LineItem(BaseModel):
    description: ExtractedField = Field(default_factory=ExtractedField)
    quantity: ExtractedField = Field(default_factory=ExtractedField)
    unit_price: ExtractedField = Field(default_factory=ExtractedField)
    line_total: ExtractedField = Field(default_factory=ExtractedField)
    tax_rate: ExtractedField | None = None


class Validation(BaseModel):
    arithmetic_ok: bool = False
    checks: list[str] = Field(default_factory=list)
    needs_review: bool = True


class InvoiceDocument(BaseModel):
    schema_version: str = SCHEMA_VERSION
    vendor: ExtractedField = Field(default_factory=ExtractedField)
    invoice_number: ExtractedField = Field(default_factory=ExtractedField)
    date: ExtractedField = Field(default_factory=ExtractedField)
    due_date: ExtractedField = Field(default_factory=ExtractedField)
    currency: ExtractedField = Field(default_factory=ExtractedField)
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: ExtractedField = Field(default_factory=ExtractedField)
    tax: ExtractedField = Field(default_factory=ExtractedField)
    total: ExtractedField = Field(default_factory=ExtractedField)
    amount_due: ExtractedField = Field(default_factory=ExtractedField)
    validation: Validation = Field(default_factory=Validation)
