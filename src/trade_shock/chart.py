"""Dependency-free SVG chart for the pilot HTS10 series."""

from __future__ import annotations

import html
from pathlib import Path


def write_pilot_chart(panel: list[dict[str, object]], output: Path, hts10: str) -> None:
    rows = [row for row in panel if row["hts10"] == hts10]
    if not rows:
        raise ValueError(f"no rows for pilot HTS10 {hts10}")
    rows.sort(key=lambda row: row["month"])
    width, height = 1100, 760
    left, right, top = 105, 30, 70
    plot_width = width - left - right
    panel_height, gap = 165, 55
    metrics = [
        ("import_value_usd", "Imports for consumption", "USD", "#2563eb"),
        ("quantity_1", "Quantity", str(rows[0]["quantity_unit"]), "#059669"),
        ("calculated_duty_usd", "Calculated duty", "USD", "#dc2626"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#172033}.title{font-size:24px;font-weight:700}.sub{font-size:13px;fill:#536071}.label{font-size:12px}.axis{stroke:#cbd5e1;stroke-width:1}.transition{fill:#f59e0b;opacity:.12}</style>',
        f'<text x="{left}" y="32" class="title">Canada → U.S. monthly trade: HTS {html.escape(hts10)}</text>',
        f'<text x="{left}" y="52" class="sub">{html.escape(str(rows[0]["hts10_description"]))}</text>',
    ]
    if rows[0].get("data_status") == "contract_fixture_not_observed":
        parts.append(
            f'<text x="{width-right}" y="32" text-anchor="end" class="sub" fill="#b45309" font-weight="700">CONTRACT TEST DATA — NOT OBSERVED</text>'
        )
    n = len(rows)
    x_positions = [left + (plot_width * i / max(n - 1, 1)) for i in range(n)]
    for index, (field, title, unit, color) in enumerate(metrics):
        y_top = top + index * (panel_height + gap)
        y_bottom = y_top + panel_height
        values = [float(row[field]) for row in rows]
        maximum = max(values) or 1.0
        parts.append(f'<text x="{left}" y="{y_top - 12}" class="label" font-weight="700">{html.escape(title)} ({html.escape(unit)})</text>')
        for tick in range(3):
            y = y_bottom - panel_height * tick / 2
            value = maximum * tick / 2
            parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="axis"/>')
            parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" class="label">{value:,.0f}</text>')
        for i, row in enumerate(rows):
            if row["is_transition_month"]:
                x0 = x_positions[i] - plot_width / max(n, 1) / 2
                parts.append(f'<rect x="{x0:.1f}" y="{y_top}" width="{plot_width/max(n,1):.1f}" height="{panel_height}" class="transition"/>')
        points = " ".join(
            f"{x_positions[i]:.1f},{(y_bottom - panel_height * value / maximum):.1f}"
            for i, value in enumerate(values)
        )
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        for i, value in enumerate(values):
            y = y_bottom - panel_height * value / maximum
            parts.append(f'<circle cx="{x_positions[i]:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
        if index == 2:
            for i, row in enumerate(rows):
                parts.append(f'<text x="{x_positions[i]:.1f}" y="{y_bottom+22}" text-anchor="middle" class="label">{html.escape(str(row["month"])[5:])}</text>')
    parts.extend([
        f'<rect x="{left}" y="{height-42}" width="14" height="14" class="transition"/>',
        f'<text x="{left+22}" y="{height-30}" class="sub">Shaded: within-month tariff change (excluded from clean full-month comparisons)</text>',
        '</svg>',
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")
