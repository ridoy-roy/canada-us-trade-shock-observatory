"""Portable text output helpers for reproducible release artifacts."""

from __future__ import annotations

import csv
from pathlib import Path


def write_text_lf(path: Path, content: str) -> None:
    """Write UTF-8 text with LF endings on every operating system."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def write_dict_rows_csv(rows: list[dict[str, object]], path: Path) -> None:
    """Write dictionary rows as a UTF-8 CSV with deterministic LF endings."""
    if not rows:
        raise ValueError("cannot write a CSV without rows")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
