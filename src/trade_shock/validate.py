"""Fail-fast checks for the V0 trade-policy panel."""

from __future__ import annotations

from collections import Counter, defaultdict


class ValidationError(ValueError):
    pass


def validate_panel(
    panel: list[dict[str, object]],
    expected_months: list[str] | None = None,
    expected_hts10: list[str] | None = None,
) -> dict[str, object]:
    errors: list[str] = []
    keys = [(row["month"], row["hts10"], row["country_code"]) for row in panel]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        errors.append(f"duplicate panel keys: {duplicates[:5]}")
    for row in panel:
        for field in ("import_value_usd", "quantity_1", "dutiable_value_usd", "calculated_duty_usd"):
            if row[field] < 0:
                errors.append(f"negative {field} at {row['month']}/{row['hts10']}")
        if row["country_code"] != "1220":
            errors.append(f"non-Canada country code {row['country_code']}")
        if not row["is_section232_core_steel"]:
            errors.append(f"out-of-scope HTS10 {row['hts10']}")
        if row["is_transition_month"] != (row["month"] in {"2025-03", "2025-06"}):
            errors.append(f"incorrect transition flag for {row['month']}")
        if row["is_transition_month"] and row["section232_rate_clean_month"] is not None:
            errors.append(f"transition month has clean rate at {row['month']}")
    if expected_months and expected_hts10:
        expected = {(month, hts) for month in expected_months for hts in expected_hts10}
        actual = {(row["month"], row["hts10"]) for row in panel}
        missing = sorted(expected - actual)
        if missing:
            errors.append(f"missing month/HTS observations: {missing[:10]}")
    units: dict[str, set[object]] = defaultdict(set)
    for row in panel:
        units[str(row["hts10"])].add(row["quantity_unit"])
    inconsistent = {code: sorted(values) for code, values in units.items() if len(values) > 1}
    if inconsistent:
        errors.append(f"inconsistent quantity units: {inconsistent}")
    report = {
        "status": "passed" if not errors else "failed",
        "row_count": len(panel),
        "panel_key_unique": not duplicates,
        "all_canada": all(row["country_code"] == "1220" for row in panel),
        "all_core_steel": all(row["is_section232_core_steel"] for row in panel),
        "transition_months": sorted({row["month"] for row in panel if row["is_transition_month"]}),
        "errors": errors,
    }
    if errors:
        raise ValidationError("; ".join(errors))
    return report

