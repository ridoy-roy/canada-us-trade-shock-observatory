"""Build the official 2025 HTS10 core-steel universe from Census concordance."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .io_utils import write_text_lf


CONCORDANCE_URL = "https://www.census.gov/trade/downloads/concordance/comm_month/2025/CONCCOMM2501.ZIP"


def parse_commodity_concordance(
    archive: Path, ranges: list[tuple[int, int, str]]
) -> list[dict[str, object]]:
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != 1:
            raise ValueError("commodity concordance archive must contain exactly one file")
        lines = bundle.read(names[0]).decode("latin-1").splitlines()
    result = []
    for line in lines:
        if not line.startswith("2") or len(line) < 248:
            continue
        hts10 = line[1:11]
        if not hts10.isdigit():
            continue
        hs6 = hts10[:6]
        matches = [note for start, end, note in ranges if start <= int(hs6) <= end]
        if not matches:
            continue
        result.append(
            {
                "hts10": hts10,
                "hs6": hs6,
                "description": line[13:163].strip(),
                "short_description": line[164:214].strip(),
                "quantity_unit_1": line[215:218].strip(),
                "quantity_unit_2": line[219:222].strip(),
                "sitc": line[223:228].strip(),
                "end_use": line[229:234].strip(),
                "naics": line[239:245].strip(),
                "hts_vintage": 2025,
                "scope": "section232_core_steel",
                "scope_basis": "; ".join(matches),
            }
        )
    if len({row["hts10"] for row in result}) != len(result):
        raise ValueError("duplicate import HTS10 codes in concordance")
    return sorted(result, key=lambda row: row["hts10"])


def write_concordance_metadata(archive: Path, output: Path) -> None:
    payload = archive.read_bytes()
    metadata = {
        "source_url": CONCORDANCE_URL,
        "source_description": "January 2025 Census Commodity Concordance",
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }
    write_text_lf(output, json.dumps(metadata, indent=2) + "\n")


def ensure_commodity_concordance(
    raw_folder: Path,
    opener=urlopen,
) -> Path:
    """Return an official concordance, downloading a content-addressed copy if needed."""
    raw_folder.mkdir(parents=True, exist_ok=True)
    candidates = sorted(raw_folder.glob("CONCCOMM2501*.ZIP"))
    if candidates:
        # Existing archives are immutable inputs. Parsing also verifies ZIP structure.
        with zipfile.ZipFile(candidates[0]) as bundle:
            if len(bundle.namelist()) != 1:
                raise ValueError("commodity concordance archive must contain exactly one file")
        return candidates[0]
    request = Request(CONCORDANCE_URL, headers={"User-Agent": "trade-shock-v0/0.2"})
    try:
        with opener(request, timeout=120) as response:
            payload = response.read()
    except HTTPError as exc:
        raise RuntimeError(f"Census concordance download failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Census concordance server: {exc.reason}") from exc
    digest = hashlib.sha256(payload).hexdigest()
    archive = raw_folder / f"CONCCOMM2501-{digest[:16]}.ZIP"
    if not archive.exists():
        with archive.open("xb") as handle:
            handle.write(payload)
    # Validate before accepting the download as a source artifact.
    with zipfile.ZipFile(archive) as bundle:
        if len(bundle.namelist()) != 1:
            raise ValueError("downloaded commodity concordance has an unexpected structure")
    write_concordance_metadata(archive, archive.with_suffix(".metadata.json"))
    return archive
