"""Transform Census response rows into the V0 trade-policy panel."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .harmonize import classify_core_steel
from .policy import monthly_policy


NUMERIC_FIELDS = ("CON_VAL_MO", "CON_QY1_MO", "DUT_VAL_MO", "CAL_DUT_MO")


def _integer(value: str, field: str) -> int:
    try:
        parsed = int(value or 0)
    except ValueError as exc:
        raise ValueError(f"{field} must be an integer, got {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"{field} cannot be negative")
    return parsed


def build_panel(
    rows: list[dict[str, str]], ranges: list[tuple[int, int, str]]
) -> list[dict[str, object]]:
    """Aggregate rate-provision rows to HTS10-country-month observations."""
    grouped: dict[tuple[str, ...], dict[str, object]] = {}
    rate_provisions: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for source in rows:
        month = f"{source['YEAR']}-{source['MONTH'].zfill(2)}"
        key = (
            month,
            source["I_COMMODITY"],
            source["CTY_CODE"],
            source["UNIT_QY1"],
            source["I_COMMODITY_LDESC"],
        )
        if key not in grouped:
            grouped[key] = {
                "month": month,
                "country_code": source["CTY_CODE"],
                "country_name": source["CTY_NAME"],
                "hts10_description": source["I_COMMODITY_LDESC"],
                "quantity_unit": source["UNIT_QY1"],
                "import_value_usd": 0,
                "quantity_1": 0,
                "dutiable_value_usd": 0,
                "calculated_duty_usd": 0,
                "source_last_update": source["LAST_UPDATE"],
                "source_row_count": 0,
                "_summary_count": 0,
                "_summary_values": {},
                "_detail_totals": {field: 0 for field in NUMERIC_FIELDS},
            }
            grouped[key].update(classify_core_steel(source["I_COMMODITY"], ranges))
        target = grouped[key]
        values = {field: _integer(source[field], field) for field in NUMERIC_FIELDS}
        if source["RP"] == "-":
            target["_summary_count"] += 1
            target["_summary_values"] = values
        else:
            for field, value in values.items():
                target["_detail_totals"][field] += value
        target["source_row_count"] += 1
        rate_provisions[key].add(source["RP"])

    panel = []
    for key, target in grouped.items():
        if target["_summary_count"] > 1:
            raise ValueError(f"multiple Census RP summary rows for {key}")
        selected = target["_summary_values"] if target["_summary_count"] else target["_detail_totals"]
        if target["_summary_count"] and selected != target["_detail_totals"]:
            raise ValueError(f"Census RP summary/detail mismatch for {key}")
        target["import_value_usd"] = selected["CON_VAL_MO"]
        target["quantity_1"] = selected["CON_QY1_MO"]
        target["dutiable_value_usd"] = selected["DUT_VAL_MO"]
        target["calculated_duty_usd"] = selected["CAL_DUT_MO"]
        del target["_summary_count"]
        del target["_summary_values"]
        del target["_detail_totals"]
        year, month = map(int, target["month"].split("-"))
        target.update(monthly_policy(year, month))
        target["rate_provisions"] = "|".join(sorted(rate_provisions[key]))
        target["observed_effective_duty_rate"] = (
            target["calculated_duty_usd"] / target["import_value_usd"]
            if target["import_value_usd"]
            else None
        )
        target["period_start"] = date(year, month, 1).isoformat()
        panel.append(target)
    return sorted(panel, key=lambda row: (row["month"], row["hts10"], row["country_code"]))
