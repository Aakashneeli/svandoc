"""Advanced table extraction helpers for OCR structured payloads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


HEADER_ALIASES: dict[str, set[str]] = {
    "description": {
        "description",
        "item",
        "item description",
        "particulars",
        "details",
        "product",
        "service",
        "name",
    },
    "quantity": {"qty", "qty.", "quantity", "q'ty", "units"},
    "unit_price": {"unit price", "price", "rate", "unit rate", "unit_price"},
    "line_total": {"line total", "line amount", "amount", "total", "extended"},
    "tax_rate": {"tax", "tax rate", "tax %", "vat", "gst"},
    "category": {"category", "dept", "department", "group"},
}

SUMMARY_ROW_MARKERS = {
    "subtotal",
    "tax",
    "total",
    "grand total",
    "amount due",
    "balance due",
}


@dataclass(frozen=True)
class TableSegment:
    page_number: int
    table_id: str
    headers: list[str]
    rows: list[list[str]]


def extract_line_items_from_tables(
    *,
    structured_payload: dict[str, Any],
    include_category: bool,
) -> list[dict[str, Any]]:
    """Extract canonical line items from advanced table structures.

    The function supports:
    1. Multi-page stitching when table segments share table_id/header signature.
    2. Merged-cell expansion via `rowspan` and `colspan`-style metadata on cells.
    """
    segments = _parse_table_segments(structured_payload)
    if not segments:
        return []

    stitched_segments = _stitch_table_segments(segments)
    line_items: list[dict[str, Any]] = []
    for segment in stitched_segments:
        for row in segment.rows:
            mapped = _map_row_to_line_item(
                row=row,
                headers=segment.headers,
                include_category=include_category,
            )
            if mapped is not None:
                line_items.append(mapped)
    return line_items


def _parse_table_segments(structured_payload: dict[str, Any]) -> list[TableSegment]:
    raw_tables: Any = (
        structured_payload.get("tables")
        or structured_payload.get("table_blocks")
        or structured_payload.get("table_pages")
    )
    if not isinstance(raw_tables, list):
        return []

    segments: list[TableSegment] = []
    for raw in raw_tables:
        if not isinstance(raw, dict):
            continue
        headers = _coerce_headers(raw.get("headers") or raw.get("columns"))
        rows = _coerce_rows(raw.get("rows"), headers)
        if not headers and rows:
            headers = [f"col_{index}" for index in range(len(rows[0]))]
        if not rows:
            continue

        cleaned_rows = _remove_repeated_header_rows(rows, headers)
        if not cleaned_rows:
            continue

        table_id = str(raw.get("table_id") or raw.get("id") or "").strip()
        page_number = _coerce_int(raw.get("page_number") or raw.get("page") or raw.get("page_index"), default=0)
        segments.append(
            TableSegment(
                page_number=page_number,
                table_id=table_id,
                headers=headers,
                rows=cleaned_rows,
            )
        )
    return segments


def _stitch_table_segments(segments: list[TableSegment]) -> list[TableSegment]:
    groups: dict[tuple[str, str], list[TableSegment]] = {}
    for segment in segments:
        header_signature = _header_signature(segment.headers)
        identity = segment.table_id or header_signature
        key = (identity, header_signature)
        groups.setdefault(key, []).append(segment)

    stitched: list[TableSegment] = []
    for grouped in groups.values():
        grouped.sort(key=lambda item: (item.page_number, item.table_id))
        base = grouped[0]
        rows: list[list[str]] = []
        for segment in grouped:
            rows.extend(segment.rows)
        stitched.append(
            TableSegment(
                page_number=base.page_number,
                table_id=base.table_id,
                headers=base.headers,
                rows=rows,
            )
        )
    return stitched


def _map_row_to_line_item(
    *,
    row: list[str],
    headers: list[str],
    include_category: bool,
) -> dict[str, Any] | None:
    if not row:
        return None

    positions = _field_positions(headers, len(row))
    description = _string_at(row, positions.get("description", 0))
    quantity = _number_at(row, positions.get("quantity"))
    unit_price = _number_at(row, positions.get("unit_price"))
    line_total = _number_at(row, positions.get("line_total"))

    if quantity is None:
        quantity = 1.0
    if unit_price is None:
        unit_price = 0.0
    if line_total is None:
        line_total = round(quantity * unit_price, 2)

    if not description:
        # Fall back to first non-empty cell when header mapping is weak.
        description = next((value for value in row if value.strip()), "")
    if not description:
        return None

    lowered = description.strip().lower()
    if lowered in SUMMARY_ROW_MARKERS and unit_price == 0.0 and quantity in {0.0, 1.0}:
        return None

    line_item: dict[str, Any] = {
        "description": description,
        "quantity": quantity,
        "unit_price": unit_price,
        "line_total": line_total,
    }
    if include_category:
        category = _string_at(row, positions.get("category"))
        line_item["category"] = category or None
    else:
        tax_rate = _number_at(row, positions.get("tax_rate"))
        line_item["tax_rate"] = tax_rate
    return line_item


def _field_positions(headers: list[str], row_width: int) -> dict[str, int]:
    if not headers:
        return {
            "description": 0,
            "quantity": 1 if row_width > 1 else 0,
            "unit_price": 2 if row_width > 2 else 0,
            "line_total": 3 if row_width > 3 else max(row_width - 1, 0),
        }

    normalized_headers = [_normalize_header_token(header) for header in headers]
    positions: dict[str, int] = {}
    for field, aliases in HEADER_ALIASES.items():
        for index, header in enumerate(normalized_headers):
            if header in aliases:
                positions[field] = index
                break

    if "description" not in positions:
        positions["description"] = 0
    if "quantity" not in positions and row_width > 1:
        positions["quantity"] = 1
    if "unit_price" not in positions and row_width > 2:
        positions["unit_price"] = 2
    if "line_total" not in positions:
        positions["line_total"] = 3 if row_width > 3 else max(row_width - 1, 0)
    return positions


def _coerce_headers(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    headers = [str(item).strip() for item in value if str(item).strip()]
    return headers


def _coerce_rows(value: Any, headers: list[str]) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    if all(isinstance(item, dict) for item in value):
        effective_headers = headers or [str(key) for key in value[0].keys()]
        output: list[list[str]] = []
        for row in value:
            assert isinstance(row, dict)
            output.append([str(row.get(header, "")).strip() for header in effective_headers])
        return output

    if all(isinstance(item, list) for item in value):
        return _expand_merged_rows(value)

    return []


def _expand_merged_rows(raw_rows: list[Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    active_rowspans: dict[int, tuple[str, int]] = {}

    for raw in raw_rows:
        if not isinstance(raw, list):
            continue

        row_cells: dict[int, str] = {}
        for column, (cell_text, remaining) in list(active_rowspans.items()):
            row_cells[column] = cell_text
            if remaining <= 1:
                del active_rowspans[column]
            else:
                active_rowspans[column] = (cell_text, remaining - 1)

        cursor = 0
        for cell in raw:
            while cursor in row_cells:
                cursor += 1
            text, col_span, row_span = _parse_cell(cell)
            for offset in range(col_span):
                col = cursor + offset
                row_cells[col] = text
                if row_span > 1:
                    active_rowspans[col] = (text, row_span - 1)
            cursor += col_span

        if not row_cells:
            continue
        max_col = max(row_cells.keys())
        rows.append([row_cells.get(index, "").strip() for index in range(max_col + 1)])

    return rows


def _parse_cell(cell: Any) -> tuple[str, int, int]:
    if isinstance(cell, dict):
        text = str(
            cell.get("text")
            or cell.get("value")
            or cell.get("content")
            or ""
        ).strip()
        col_span = _coerce_int(cell.get("colspan") or cell.get("col_span"), default=1)
        row_span = _coerce_int(cell.get("rowspan") or cell.get("row_span"), default=1)
        return text, max(col_span, 1), max(row_span, 1)

    return str(cell or "").strip(), 1, 1


def _remove_repeated_header_rows(rows: list[list[str]], headers: list[str]) -> list[list[str]]:
    if not headers:
        return rows
    normalized_headers = [_normalize_header_token(item) for item in headers]
    cleaned: list[list[str]] = []
    for row in rows:
        normalized_row = [_normalize_header_token(item) for item in row[: len(headers)]]
        if normalized_row == normalized_headers:
            continue
        cleaned.append(row)
    return cleaned


def _header_signature(headers: list[str]) -> str:
    return "|".join(_normalize_header_token(value) for value in headers)


def _normalize_header_token(value: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()
    return " ".join(compact.split())


def _string_at(row: list[str], index: int | None) -> str:
    if index is None or index < 0 or index >= len(row):
        return ""
    return str(row[index]).strip()


def _number_at(row: list[str], index: int | None) -> float | None:
    text = _string_at(row, index)
    if not text:
        return None
    return _parse_number(text)


def _parse_number(value: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = text.replace(",", "")
    text = text.replace("$", "")
    text = text.replace("€", "")
    text = text.replace("£", "")
    try:
        parsed = float(text)
    except ValueError:
        return None
    return -parsed if negative else parsed


def _coerce_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed
