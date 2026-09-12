"""HTS10 normalization and HS6/core-steel mapping scaffolding."""

from __future__ import annotations

import csv
from pathlib import Path


def normalize_hts10(value: str) -> str:
    digits = "".join(character for character in str(value) if character.isdigit())
    if len(digits) != 10:
        raise ValueError(f"HTS10 must resolve to 10 digits, got {value!r}")
    return digits


def hs6_from_hts10(hts10: str) -> str:
    return normalize_hts10(hts10)[:6]


def load_core_ranges(path: Path | str) -> list[tuple[int, int, str]]:
    ranges = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            ranges.append((int(row["hs6_start"]), int(row["hs6_end"]), row["note"]))
    return ranges


def classify_core_steel(hts10: str, ranges: list[tuple[int, int, str]]) -> dict[str, object]:
    normalized = normalize_hts10(hts10)
    hs6 = normalized[:6]
    matches = [note for start, end, note in ranges if start <= int(hs6) <= end]
    return {
        "hts10": normalized,
        "hs6": hs6,
        "hts_vintage": 2025,
        "hs6_harmonization_method": "prefix",
        "is_section232_core_steel": bool(matches),
        "core_steel_range_note": "; ".join(matches),
        "concordance_status": "same-vintage; future crosswalk required for longitudinal revisions",
    }

