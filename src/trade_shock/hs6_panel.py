"""HS6 production panel and monthly core-steel summary."""

from __future__ import annotations

from collections import Counter

from .harmonize import load_core_ranges
from .policy import monthly_policy


SOURCE_TO_OUTPUT = {
    "CON_VAL_MO": "import_value_usd",
    "CON_QY1_MO": "quantity_1",
    "DUT_VAL_MO": "dutiable_value_usd",
    "CAL_DUT_MO": "calculated_duty_usd",
}


def _number(value: str, field: str) -> int:
    try:
        result = int(value or 0)
    except ValueError as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if result < 0:
        raise ValueError(f"{field} cannot be negative")
    return result


def build_hs6_panel(
    rows: list[dict[str, str]], ranges: list[tuple[int, int, str]]
) -> list[dict[str, object]]:
    panel = []
    for source in rows:
        code = source["I_COMMODITY"]
        if len(code) != 6 or not code.isdigit():
            continue
        matches = [note for start, end, note in ranges if start <= int(code) <= end]
        if not matches:
            continue
        if source["CTY_CODE"] != "1220" or source["RP"] != "-":
            raise ValueError("HS6 release input must contain Canada RP total rows only")
        year, month = int(source["YEAR"]), int(source["MONTH"])
        target: dict[str, object] = {
            "month": f"{year}-{month:02d}",
            "period_start": f"{year}-{month:02d}-01",
            "country_code": "1220",
            "country_name": source["CTY_NAME"],
            "commodity_level": "HS6",
            "hs6": code,
            "hs6_description": source["I_COMMODITY_LDESC"],
            "quantity_unit": source["UNIT_QY1"],
            "hts_vintage": year,
            "is_section232_core_steel": True,
            "scope_basis": "; ".join(matches),
            "source_rate_provision": "-",
            "source_last_update": source["LAST_UPDATE"],
            "data_status": "official_census_api",
        }
        for source_field, output_field in SOURCE_TO_OUTPUT.items():
            if source_field == "CON_QY1_MO" and source["UNIT_QY1"] == "-":
                target[output_field] = None
            else:
                target[output_field] = _number(source[source_field], source_field)
        target.update(monthly_policy(year, month))
        target["observed_effective_duty_rate"] = (
            target["calculated_duty_usd"] / target["import_value_usd"]
            if target["import_value_usd"]
            else None
        )
        panel.append(target)
    keys = [(row["month"], row["hs6"]) for row in panel]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate HS6 panel keys: {duplicates[:5]}")
    return sorted(panel, key=lambda row: (row["month"], row["hs6"]))


def summarize_monthly(panel: list[dict[str, object]]) -> list[dict[str, object]]:
    months: dict[str, list[dict[str, object]]] = {}
    for row in panel:
        months.setdefault(str(row["month"]), []).append(row)
    summary = []
    for month, rows in sorted(months.items()):
        reported_quantities = [row for row in rows if row["quantity_1"] is not None]
        units = {row["quantity_unit"] for row in reported_quantities}
        if units - {"KG"}:
            raise ValueError(f"non-KG quantity in core-steel aggregation for {month}: {units}")
        value = sum(int(row["import_value_usd"]) for row in rows)
        duty = sum(int(row["calculated_duty_usd"]) for row in rows)
        quantity = (
            sum(int(row["quantity_1"]) for row in reported_quantities)
            if len(reported_quantities) == len(rows)
            else None
        )
        result = {
            "month": month,
            "period_start": f"{month}-01",
            "import_value_usd": value,
            "quantity_kg": quantity,
            "calculated_duty_usd": duty,
            "observed_effective_duty_rate": duty / value if value else None,
            "observed_effective_duty_rate_pct": 100 * duty / value if value else None,
            "reported_hs6_count": len(rows),
            "positive_trade_hs6_count": sum(bool(row["import_value_usd"]) for row in rows),
        }
        result.update(monthly_policy(*map(int, month.split("-"))))
        summary.append(result)
    by_month = {row["month"]: row for row in summary}
    for row in summary:
        year, month = map(int, str(row["month"]).split("-"))
        prior = by_month.get(f"{year - 1}-{month:02d}")
        row["import_value_yoy_change"] = (
            row["import_value_usd"] / prior["import_value_usd"] - 1
            if prior and prior["import_value_usd"]
            else None
        )
        row["quantity_yoy_change"] = None
    return summary


def summarize_product_changes(
    panel: list[dict[str, object]],
    base_year: int = 2024,
    current_year: int = 2025,
    limit: int = 10,
) -> list[dict[str, object]]:
    """Rank HS6 products by their contribution to the decline in import value."""
    concise_names = {
        "721049": "Zinc-coated flat-rolled steel",
        "730661": "Welded rectangular steel tube",
        "720837": "Hot-rolled coil, 4.75-10 mm",
        "722530": "Hot-rolled alloy-steel coil",
        "720838": "Hot-rolled coil, 3-4.75 mm",
        "720917": "Cold-rolled coil, 0.5-1 mm",
        "721391": "Hot-rolled bars/rods, under 14 mm",
        "720839": "Hot-rolled coil, under 3 mm",
        "720916": "Cold-rolled coil, 1-3 mm",
        "720712": "Semifinished rectangular steel",
    }
    if limit <= 0:
        raise ValueError("limit must be positive")
    products: dict[str, dict[str, object]] = {}
    for row in panel:
        year = int(str(row["month"])[:4])
        if year not in {base_year, current_year}:
            continue
        code = str(row["hs6"])
        target = products.setdefault(
            code,
            {
                "hs6": code,
                "product_name": concise_names.get(code, str(row["hs6_description"]).title()),
                "hs6_description": str(row["hs6_description"]),
                "base_year_value_usd": 0,
                "current_year_value_usd": 0,
            },
        )
        field = "base_year_value_usd" if year == base_year else "current_year_value_usd"
        target[field] = int(target[field]) + int(row["import_value_usd"])
    total_base = sum(int(row["base_year_value_usd"]) for row in products.values())
    total_current = sum(int(row["current_year_value_usd"]) for row in products.values())
    total_decline = total_base - total_current
    results = []
    for row in products.values():
        base = int(row["base_year_value_usd"])
        current = int(row["current_year_value_usd"])
        change = current - base
        results.append(
            {
                **row,
                "change_usd": change,
                "change_pct": current / base - 1 if base else None,
                "share_of_total_decline_pct": 100 * (-change) / total_decline if total_decline else None,
            }
        )
    ranked = sorted(results, key=lambda row: (int(row["change_usd"]), str(row["hs6"])))[:limit]
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
        row["base_year"] = base_year
        row["current_year"] = current_year
    field_order = [
        "rank", "hs6", "product_name", "hs6_description", "base_year", "current_year",
        "base_year_value_usd", "current_year_value_usd", "change_usd",
        "change_pct", "share_of_total_decline_pct",
    ]
    return [{field: row[field] for field in field_order} for row in ranked]


def validate_release(
    panel: list[dict[str, object]], summary: list[dict[str, object]], expected_months: list[str]
) -> dict[str, object]:
    errors = []
    actual_months = sorted({str(row["month"]) for row in panel})
    missing = sorted(set(expected_months) - set(actual_months))
    if missing:
        errors.append(f"missing months: {missing}")
    if any(not row["is_section232_core_steel"] for row in panel):
        errors.append("out-of-scope rows present")
    if any(row["country_code"] != "1220" for row in panel):
        errors.append("non-Canada rows present")
    if any(row["is_transition_month"] != (row["month"] in {"2025-03", "2025-06"}) for row in panel):
        errors.append("transition flag mismatch")
    if len(summary) != len(expected_months):
        errors.append("monthly summary is incomplete")
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "passed",
        "errors": [],
        "panel_rows": len(panel),
        "months": len(actual_months),
        "hs6_codes": len({row["hs6"] for row in panel}),
        "country_code": "1220",
        "scope": "section232_core_steel",
        "transition_months": ["2025-03", "2025-06"],
        "hs6_quantity_available": all(row["quantity_1"] is not None for row in panel),
    }
