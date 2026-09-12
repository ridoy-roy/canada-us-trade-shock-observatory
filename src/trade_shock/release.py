"""Release artifacts: charts and concise analytical report."""

from __future__ import annotations

import html
import json
from pathlib import Path


def write_monthly_chart(rows: list[dict[str, object]], output: Path) -> None:
    width, height = 1200, 780
    left, right, top = 110, 35, 75
    plot_width = width - left - right
    panel_height, gap = 165, 58
    metrics = [
        ("import_value_usd", "Imports for consumption", "USD", "#2563eb"),
        ("observed_effective_duty_rate_pct", "Observed effective duty rate", "%", "#7c3aed"),
        ("calculated_duty_usd", "Calculated duty", "USD", "#dc2626"),
    ]
    n = len(rows)
    xs = [left + plot_width * index / max(n - 1, 1) for index in range(n)]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#172033}.title{font-size:25px;font-weight:700}.sub{font-size:13px;fill:#536071}.label{font-size:11px}.axis{stroke:#cbd5e1}.transition{fill:#f59e0b;opacity:.14}.policy{stroke:#7c3aed;stroke-width:1.5;stroke-dasharray:5 4}</style>',
        f'<text x="{left}" y="32" class="title">Canadian core steel imports into the United States</text>',
        f'<text x="{left}" y="53" class="sub">Official Census data · HS6 core scope · monthly, 2024–2025</text>',
    ]
    for metric_index, (field, title, unit, color) in enumerate(metrics):
        y_top = top + metric_index * (panel_height + gap)
        y_bottom = y_top + panel_height
        values = [float(row[field]) for row in rows]
        maximum = max(values) or 1
        parts.append(f'<text x="{left}" y="{y_top-12}" class="label" font-weight="700">{title} ({unit})</text>')
        for tick in range(3):
            y = y_bottom - panel_height * tick / 2
            label = maximum * tick / 2
            parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="axis"/>')
            parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" class="label">{label:,.0f}</text>')
        for i, row in enumerate(rows):
            if row["is_transition_month"]:
                span = plot_width / max(n - 1, 1)
                parts.append(f'<rect x="{xs[i]-span/2:.1f}" y="{y_top}" width="{span:.1f}" height="{panel_height}" class="transition"/>')
        for event_month in ("2025-03", "2025-06"):
            index = next((i for i, row in enumerate(rows) if row["month"] == event_month), None)
            if index is not None:
                parts.append(f'<line x1="{xs[index]:.1f}" y1="{y_top}" x2="{xs[index]:.1f}" y2="{y_bottom}" class="policy"/>')
        points = " ".join(f"{xs[i]:.1f},{y_bottom-panel_height*value/maximum:.1f}" for i, value in enumerate(values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        if metric_index == 2:
            for i, row in enumerate(rows):
                if i % 2 == 0 or i == n - 1:
                    parts.append(f'<text x="{xs[i]:.1f}" y="{y_bottom+22}" text-anchor="middle" class="label">{html.escape(str(row["month"]))}</text>')
    parts.extend([
        f'<rect x="{left}" y="{height-39}" width="14" height="14" class="transition"/>',
        f'<text x="{left+22}" y="{height-27}" class="sub">Transition months (March and June 2025); excluded from clean full-month comparisons</text>',
        '</svg>',
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")


def write_product_decline_chart(rows: list[dict[str, object]], output: Path) -> None:
    """Write a horizontal bar chart of the HS6 products driving the value decline."""
    width, height = 1200, 690
    left, right, top, bottom = 345, 90, 105, 65
    plot_width = width - left - right
    row_height = (height - top - bottom) / max(len(rows), 1)
    magnitudes = [max(0, -int(row["change_usd"])) for row in rows]
    maximum = max(magnitudes) or 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#172033}.title{font-size:25px;font-weight:700}.sub{font-size:13px;fill:#536071}.code{font-size:14px;font-weight:700}.label{font-size:12px}.grid{stroke:#e2e8f0}.bar{fill:#2563eb}</style>',
        f'<text x="{left}" y="38" class="title">Largest HS6 contributors to the 2025 import-value decline</text>',
        f'<text x="{left}" y="62" class="sub">2025 value minus 2024 value; Canadian core-steel imports for consumption</text>',
    ]
    for tick in range(5):
        value = maximum * tick / 4
        x = left + plot_width * tick / 4
        parts.append(f'<line x1="{x:.1f}" y1="{top-12}" x2="{x:.1f}" y2="{height-bottom}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{height-bottom+25}" text-anchor="middle" class="label">${value/1_000_000:.0f}M</text>')
    for index, (row, magnitude) in enumerate(zip(rows, magnitudes)):
        y = top + index * row_height
        bar_width = plot_width * magnitude / maximum
        product_label = f'{row["hs6"]}  {row["product_name"]}'
        parts.append(f'<text x="{left-12}" y="{y+row_height*.58:.1f}" text-anchor="end" class="code">{html.escape(product_label)}</text>')
        parts.append(f'<rect x="{left}" y="{y+row_height*.18:.1f}" width="{bar_width:.1f}" height="{row_height*.52:.1f}" rx="3" class="bar"/>')
        parts.append(f'<text x="{left+bar_width+8:.1f}" y="{y+row_height*.58:.1f}" class="label">-${magnitude/1_000_000:.1f}M</text>')
    parts.extend([
        f'<text x="{left}" y="{height-14}" class="sub">Bars show absolute contribution to the aggregate decline; they do not represent causal effects.</text>',
        '</svg>',
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")


def write_release_report(
    universe: list[dict[str, object]],
    panel: list[dict[str, object]],
    summary: list[dict[str, object]],
    product_changes: list[dict[str, object]],
    validation: dict[str, object],
    output: Path,
) -> None:
    annual = {}
    for year in (2024, 2025):
        rows = [row for row in summary if str(row["month"]).startswith(str(year))]
        annual[year] = {
            "value": sum(int(row["import_value_usd"]) for row in rows),
            "duty": sum(int(row["calculated_duty_usd"]) for row in rows),
        }
    def pct(current: int, previous: int) -> str:
        return f"{(current / previous - 1):+.1%}" if previous else "n/a"
    summary_by_month = {str(row["month"]): row for row in summary}
    regimes = [
        ("Pre-tariff clean months", [1, 2]),
        ("25% clean months", [4, 5]),
        ("50% clean months", [7, 8, 9, 10, 11, 12]),
    ]
    regime_lines = []
    for label, months in regimes:
        current_rows = [summary_by_month[f"2025-{month:02d}"] for month in months]
        prior_rows = [summary_by_month[f"2024-{month:02d}"] for month in months]
        current_value = sum(int(row["import_value_usd"]) for row in current_rows)
        prior_value = sum(int(row["import_value_usd"]) for row in prior_rows)
        duty = sum(int(row["calculated_duty_usd"]) for row in current_rows)
        effective = duty / current_value if current_value else 0
        regime_lines.append(
            f"| {label} | ${current_value:,} | {pct(current_value, prior_value)} | {effective:.1%} |"
        )
    product_lines = [
        f"| {row['rank']} | {row['hs6']} | {row['product_name']} | ${int(row['base_year_value_usd']):,} | "
        f"${int(row['current_year_value_usd']):,} | -${abs(int(row['change_usd'])):,} | "
        f"{float(row['share_of_total_decline_pct']):.1f}% |"
        for row in product_changes
    ]
    report = f"""# Canada-U.S. Trade Shock Observatory: Initial Analytical Release

**Ridoy Roy**

## Release status

- Validation: **{validation['status']}**
- Official Census observations: **{len(panel):,}** HS6-month rows
- Coverage: **{validation['months']} months**, January 2024–December 2025
- Product universe: **{len(universe):,} HTS10 lines** mapping to **{len({row['hs6'] for row in universe})} HS6 codes**
- Policy transitions: March 12 and June 4, 2025; both transition months are flagged and excluded from clean-month comparisons.

## Descriptive results

| Year | Import value | Calculated duty |
|---|---:|---:|
| 2024 | ${annual[2024]['value']:,} | ${annual[2024]['duty']:,} |
| 2025 | ${annual[2025]['value']:,} | ${annual[2025]['duty']:,} |

The value of imports in scope was **{-1 * (annual[2025]['value'] / annual[2024]['value'] - 1):.1%} lower** in 2025 than in 2024. This comparison is descriptive. Census calculated duty can include duties beyond Section 232, so it should not be read as a stand-alone measure of the steel tariff.

### Clean-month regime comparison

| 2025 regime window | Import value | Change from same 2024 months | Observed duty/value |
|---|---:|---:|---:|
{chr(10).join(regime_lines)}

The year-over-year decline is larger in each successive window. The reported duty-to-value ratio remains below the headline statutory rate because entries can differ in treatment and timing, and because other provisions may apply. March and June are left out of this comparison because the tariff changed during those months.

## Products contributing most to the decline

| Rank | HS6 | Product | 2024 value | 2025 value | Change | Share of aggregate decline |
|---:|---:|---|---:|---:|---:|---:|
{chr(10).join(product_lines)}

The ranking is an accounting decomposition of the value change, not an estimate of each product's causal response to the tariff.

## Interpretation boundaries

- The product universe is the January 2025 Census import concordance filtered to the Proclamation 9705 core steel HS6 ranges; derivative articles are excluded.
- Trade data are imports for consumption from Canada (`CTY_CODE=1220`) and use Census `RP="-"` total rows to avoid double-counting rate-provision breakdowns.
- Census does not report quantity for the HS6 aggregate rows (`UNIT_QY1="-"`), so full-scope quantity is recorded as unavailable rather than as zero. The HTS10 pilot panel retains its reported kilogram quantity series.
- HTS10 lines are mapped to HS6 by prefix. Cross-vintage identity remains explicit through the `hts_vintage` field.
- March and June 2025 contain within-month policy changes. Their day-weighted policy rates are descriptive only.
- No causal claim is made without a control group and a formally specified counterfactual design.
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    (output.parent / "annual_summary.json").write_text(json.dumps(annual, indent=2) + "\n", encoding="utf-8")
