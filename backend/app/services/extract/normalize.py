"""Shared post-processing applied to EVERY extractor's output — this is what
makes the JSON consistent regardless of which extractor produced it.

Standard (Western) digits only. Handles decimal-separator variants and the
Tunisian Dinar's 3-decimal millimes."""

from __future__ import annotations

import re

from app.schemas.invoice import InvoiceDocument, LineItem

# Reconciliation tolerance. TND carries 3 decimals (millimes); allow a small slack.
_TOL = 0.01


def parse_amount(raw) -> float | None:
    """Parse a monetary/numeric string into a float. Resolves '.' vs ',' as the
    decimal separator by taking the last-seen separator as decimal."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    # Keep digits, separators and sign only.
    s = re.sub(r"[^0-9.,\-]", "", s)
    if not s or s in {"-", ".", ","}:
        return None

    last_dot = s.rfind(".")
    last_comma = s.rfind(",")
    if last_dot == -1 and last_comma == -1:
        dec_pos = -1
    else:
        dec_pos = max(last_dot, last_comma)

    if dec_pos == -1:
        int_part, frac_part = s, ""
    else:
        int_part = s[:dec_pos]
        frac_part = s[dec_pos + 1 :]
    int_part = re.sub(r"[.,]", "", int_part)  # strip remaining thousands seps
    frac_part = re.sub(r"[.,]", "", frac_part)
    candidate = int_part + ("." + frac_part if frac_part else "")
    try:
        return float(candidate)
    except ValueError:
        return None


_NUMERIC_FIELDS = ("subtotal", "tax", "total", "amount_due")


def _coerce_field(field) -> None:
    if field is None:
        return
    if not isinstance(field.value, (int, float)):
        parsed = parse_amount(field.raw_text if field.raw_text is not None else field.value)
        if parsed is not None:
            field.value = parsed


def _coerce_line(item: LineItem) -> None:
    for f in (item.quantity, item.unit_price, item.line_total, item.tax_rate):
        _coerce_field(f)


def normalize_invoice(doc: InvoiceDocument) -> InvoiceDocument:
    """Coerce numeric fields to floats and run arithmetic reconciliation."""
    for name in _NUMERIC_FIELDS:
        _coerce_field(getattr(doc, name))
    for item in doc.line_items:
        _coerce_line(item)

    checks: list[str] = []
    ok = True

    line_sum = sum(
        li.line_total.value
        for li in doc.line_items
        if isinstance(li.line_total.value, (int, float))
    )
    subtotal = doc.subtotal.value if isinstance(doc.subtotal.value, (int, float)) else None
    tax = doc.tax.value if isinstance(doc.tax.value, (int, float)) else None
    total = doc.total.value if isinstance(doc.total.value, (int, float)) else None

    if doc.line_items and subtotal is not None:
        if abs(line_sum - subtotal) <= _TOL:
            checks.append("line items sum matches subtotal")
        else:
            ok = False
            checks.append(f"line items sum {line_sum:.3f} != subtotal {subtotal:.3f}")

    if subtotal is not None and tax is not None and total is not None:
        if abs(subtotal + tax - total) <= _TOL:
            checks.append("subtotal + tax matches total")
        else:
            ok = False
            checks.append(f"subtotal+tax {subtotal + tax:.3f} != total {total:.3f}")

    ran_any = len(checks) > 0
    doc.validation.checks = checks
    doc.validation.arithmetic_ok = ok and ran_any
    doc.validation.needs_review = not (ok and ran_any)
    return doc
