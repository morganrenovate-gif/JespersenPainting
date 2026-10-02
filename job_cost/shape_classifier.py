"""DATA-002: exact-match, metadata-only workbook shape classification.

The built-in shapes are invented synthetic examples, not validated Jespersen layouts.
This module never opens a workbook or chooses an adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

_ADDRESS = re.compile(r"[A-Z]+[1-9][0-9]*\Z")
SIGNATURE_VERSION = "workbook-structure/v1"


@dataclass(frozen=True)
class SheetStructure:
    name: str
    # (A1 cell address, literal column heading), not row values or formulas.
    headers: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class WorkbookStructure:
    sheets: tuple[SheetStructure, ...]
    # False also covers a sheet inventory or header scan that was truncated.
    complete: bool


@dataclass(frozen=True)
class ShapeClassification:
    state: str  # known or unknown
    shape_version: str | None
    signature: str | None  # None when the metadata cannot define a signature
    review_reason: str | None  # insufficient_metadata or unrecognized_shape


def structural_signature(metadata: WorkbookStructure) -> str | None:
    """Return a versioned SHA-256 signature, or None for incomplete/invalid input.

    Sheet and header enumeration order are irrelevant. Names, addresses and headings
    are exact (case/spacing sensitive); duplicates or missing fields fail closed.
    No data cells, formulas, workbook bytes, source IDs or paths are inspected.
    """
    if type(metadata) is not WorkbookStructure or metadata.complete is not True:
        return None
    if type(metadata.sheets) is not tuple or not metadata.sheets:
        return None
    sheets = []
    seen_names = set()
    for sheet in metadata.sheets:
        if type(sheet) is not SheetStructure or type(sheet.name) is not str or not sheet.name.strip():
            return None
        if sheet.name in seen_names or type(sheet.headers) is not tuple or not sheet.headers:
            return None
        seen_names.add(sheet.name)
        headers = []
        seen_addresses = set()
        for header in sheet.headers:
            if type(header) is not tuple or len(header) != 2:
                return None
            address, label = header
            if (type(address) is not str or not _ADDRESS.fullmatch(address)
                    or type(label) is not str or not label.strip()
                    or address in seen_addresses):
                return None
            seen_addresses.add(address)
            headers.append((address, label))
        sheets.append((sheet.name, sorted(headers)))
    payload = json.dumps([SIGNATURE_VERSION, sorted(sheets)], ensure_ascii=True,
                         separators=(",", ":"))
    return f"{SIGNATURE_VERSION}:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Synthetic-only structural exemplars. An exact signature match is required;
# no fuzzy/partial match and no claim that these match real client workbooks.
_SYNTHETIC_SHAPES = (
    ("synthetic-ledger/v1", WorkbookStructure((
        SheetStructure("Invented Ledger", (("A1", "Task"), ("B1", "Hours"))),
        SheetStructure("Invented Summary", (("A1", "Category"), ("B1", "Total"))),
    ), True)),
    ("synthetic-ledger/v2", WorkbookStructure((
        SheetStructure("Invented Ledger", (("A2", "Task"), ("C2", "Hours"))),
        SheetStructure("Invented Summary", (("A1", "Category"), ("B1", "Total"))),
    ), True)),
)
_KNOWN_SIGNATURES = {structural_signature(shape): version for version, shape in _SYNTHETIC_SHAPES}


def classify_shape(metadata: WorkbookStructure) -> ShapeClassification:
    """Classify only complete exact structural matches; otherwise require review."""
    signature = structural_signature(metadata)
    if signature is None:
        return ShapeClassification("unknown", None, None, "insufficient_metadata")
    version = _KNOWN_SIGNATURES.get(signature)
    if version is None:
        return ShapeClassification("unknown", None, signature, "unrecognized_shape")
    return ShapeClassification("known", version, signature, None)
