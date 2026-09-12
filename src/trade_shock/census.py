"""U.S. Census monthly import ingestion with content-addressed snapshots."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
CANADA_CODE = "1220"
FIELDS = (
    "I_COMMODITY",
    "I_COMMODITY_LDESC",
    "CTY_CODE",
    "CTY_NAME",
    "YEAR",
    "MONTH",
    "UNIT_QY1",
    "CON_VAL_MO",
    "CON_QY1_MO",
    "DUT_VAL_MO",
    "CAL_DUT_MO",
    "RP",
    "LAST_UPDATE",
)


class CensusError(RuntimeError):
    """Raised when Census data cannot be fetched or decoded."""


@dataclass(frozen=True)
class Snapshot:
    data_path: Path
    metadata_path: Path
    sha256: str


def _validate_month(month: str) -> None:
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"month must be YYYY-MM, got {month!r}") from exc


def _validate_hts10(hts10: str) -> None:
    if len(hts10) != 10 or not hts10.isdigit():
        raise ValueError(f"HTS10 must be exactly 10 digits, got {hts10!r}")


def parse_api_payload(payload: bytes) -> list[dict[str, str]]:
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CensusError("Census response was not valid JSON") from exc
    if not isinstance(decoded, list) or not decoded or not isinstance(decoded[0], list):
        raise CensusError("Census response did not have the expected row-array shape")
    header = decoded[0]
    missing = set(FIELDS) - set(header)
    if missing:
        raise CensusError(f"Census response missing fields: {sorted(missing)}")
    rows: list[dict[str, str]] = []
    for values in decoded[1:]:
        if len(values) != len(header):
            raise CensusError("Census response contains a malformed row")
        row: dict[str, str] = {}
        for name, value in zip(header, values, strict=True):
            # The HS endpoint appends predicate columns (I_COMMODITY and
            # CTY_CODE) even when they were explicitly requested. Accept the
            # duplicate only when both copies agree.
            if name in row and row[name] != value:
                raise CensusError(f"Census response has conflicting duplicate field {name}")
            row[name] = value
        rows.append(row)
    return rows


def write_immutable_snapshot(
    payload: bytes,
    raw_root: Path,
    month: str,
    hts10: str,
    request_parameters: dict[str, str],
) -> Snapshot:
    """Persist exact response bytes; never overwrite a prior representation."""
    digest = hashlib.sha256(payload).hexdigest()
    folder = raw_root / "census_imports_hs" / month
    folder.mkdir(parents=True, exist_ok=True)
    data_path = folder / f"{hts10}-{digest[:16]}.json"
    metadata_path = folder / f"{hts10}-{digest[:16]}.metadata.json"
    if data_path.exists():
        if hashlib.sha256(data_path.read_bytes()).hexdigest() != digest:
            raise CensusError(f"snapshot digest collision at {data_path}")
    else:
        with data_path.open("xb") as handle:
            handle.write(payload)
    metadata = {
        "source": API_URL,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "sha256": digest,
        "bytes": len(payload),
        "request_parameters": request_parameters,
    }
    if not metadata_path.exists():
        with metadata_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(metadata, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return Snapshot(data_path, metadata_path, digest)


class CensusClient:
    def __init__(
        self,
        api_key: str | None = None,
        raw_root: Path | str = "data/raw",
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self.api_key = api_key or os.getenv("CENSUS_API_KEY")
        self.raw_root = Path(raw_root)
        self.opener = opener

    def fetch_month(self, month: str, hts10: str) -> tuple[list[dict[str, str]], Snapshot]:
        _validate_month(month)
        _validate_hts10(hts10)
        if not self.api_key:
            raise CensusError(
                "Census now requires an API key. Set CENSUS_API_KEY or pass --api-key."
            )
        public_params = {
            "get": ",".join(FIELDS),
            "time": month,
            "I_COMMODITY": hts10,
            "CTY_CODE": CANADA_CODE,
        }
        params = {**public_params, "key": self.api_key}
        request = Request(f"{API_URL}?{urlencode(params)}", headers={"User-Agent": "trade-shock-v0/0.1"})
        try:
            with self.opener(request, timeout=60) as response:
                payload = response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise CensusError(f"Census HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise CensusError(f"Could not reach Census: {exc.reason}") from exc
        rows = parse_api_payload(payload)
        snapshot = write_immutable_snapshot(payload, self.raw_root, month, hts10, public_params)
        return rows, snapshot

    def fetch_hs6_prefix(self, month: str, prefix: str) -> tuple[list[dict[str, str]], Snapshot]:
        """Fetch Census HS6 total rows for a three-digit chapter prefix."""
        _validate_month(month)
        if len(prefix) != 3 or not prefix.isdigit():
            raise ValueError(f"HS prefix must be three digits, got {prefix!r}")
        if not self.api_key:
            raise CensusError(
                "Census now requires an API key. Set CENSUS_API_KEY or add it to .env."
            )
        pattern = f"{prefix}*"
        public_params = {
            "get": ",".join(FIELDS),
            "time": month,
            "I_COMMODITY": pattern,
            "CTY_CODE": CANADA_CODE,
            "COMM_LVL": "HS6",
            "RP": "-",
        }
        params = {**public_params, "key": self.api_key}
        request = Request(f"{API_URL}?{urlencode(params)}", headers={"User-Agent": "trade-shock-v0/0.1"})
        try:
            with self.opener(request, timeout=120) as response:
                payload = response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise CensusError(f"Census HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise CensusError(f"Could not reach Census: {exc.reason}") from exc
        rows = parse_api_payload(payload)
        snapshot = write_immutable_snapshot(
            payload, self.raw_root, month, f"hs6-{prefix}star", public_params
        )
        return rows, snapshot


def load_fixture(path: Path) -> list[dict[str, str]]:
    return parse_api_payload(path.read_bytes())
