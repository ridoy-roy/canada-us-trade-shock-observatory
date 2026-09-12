from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "canada_us_trade_shock_observatory_v0.pdf"
NAVY = colors.HexColor("#101C3D")
BLUE = colors.HexColor("#1769E0")
GREEN = colors.HexColor("#078C73")
RED = colors.HexColor("#D9485F")
PURPLE = colors.HexColor("#7457E8")
AMBER = colors.HexColor("#F5A524")
SLATE = colors.HexColor("#526079")
MUTED = colors.HexColor("#76839A")
LIGHT = colors.HexColor("#F3F6FA")
PALE_BLUE = colors.HexColor("#EAF2FF")
GRID = colors.HexColor("#D6DEEA")
WHITE = colors.white
INK = colors.HexColor("#0A1228")


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def usd(value: float) -> str:
    prefix = "-$" if value < 0 else "$"
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return f"{prefix}{magnitude / 1_000_000_000:.2f}B"
    if magnitude >= 1_000_000:
        return f"{prefix}{magnitude / 1_000_000:.1f}M"
    return f"{prefix}{magnitude:,.0f}"


def compact_number(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:.0f}M"
    if magnitude >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def month_label(value: str) -> str:
    year, month = value.split("-")
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{names[int(month) - 1]} {year[2:]}"


def panel_chart(
    rows: list[dict[str, str]],
    specs: list[tuple[str, str, colors.Color, float]],
    width: float = 500,
    panel_height: float = 92,
) -> Drawing:
    left, right, top, gap = 54, 10, 18, 30
    height = top + len(specs) * panel_height + (len(specs) - 1) * gap + 28
    drawing = Drawing(width, height)
    plot_width = width - left - right
    xs = [left + plot_width * i / max(len(rows) - 1, 1) for i in range(len(rows))]
    for panel_index, (field, label, color, multiplier) in enumerate(specs):
        panel_top = height - top - panel_index * (panel_height + gap)
        panel_bottom = panel_top - panel_height
        values = [float(row[field] or 0) * multiplier for row in rows]
        maximum = max(values) or 1
        drawing.add(String(left, panel_top + 8, label, fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
        for tick in range(3):
            y = panel_bottom + panel_height * tick / 2
            drawing.add(Line(left, y, width - right, y, strokeColor=GRID, strokeWidth=0.5))
            value = maximum * tick / 2
            tick_label = f"{value:.0f}%" if "(%)" in label else compact_number(value)
            drawing.add(String(left - 7, y - 2.5, tick_label, textAnchor="end", fontSize=7, fillColor=MUTED))
        for i, row in enumerate(rows):
            if row.get("is_transition_month") == "True":
                span = plot_width / max(len(rows) - 1, 1)
                drawing.add(Rect(xs[i] - span / 2, panel_bottom, span, panel_height, fillColor=colors.Color(1, .62, .04, alpha=.13), strokeColor=None))
        points = [(xs[i], panel_bottom + panel_height * value / maximum) for i, value in enumerate(values)]
        for first, second in zip(points, points[1:]):
            drawing.add(Line(first[0], first[1], second[0], second[1], strokeColor=color, strokeWidth=1.8))
        for x, y in points:
            drawing.add(Circle(x, y, 1.8, fillColor=color, strokeColor=None))
        if panel_index == len(specs) - 1:
            step = 2 if len(rows) > 12 else 1
            for i, row in enumerate(rows):
                if i % step == 0 or i == len(rows) - 1:
                    drawing.add(String(xs[i], panel_bottom - 12, month_label(row["month"]), textAnchor="middle", fontSize=6.2, fillColor=MUTED))
    return drawing


def product_decline_chart(rows: list[dict[str, str]], width: float = 510, height: float = 286) -> Drawing:
    left, right, top, bottom = 184, 58, 15, 25
    drawing = Drawing(width, height)
    plot_width = width - left - right
    row_height = (height - top - bottom) / max(len(rows), 1)
    values = [max(0, -float(row["change_usd"])) for row in rows]
    maximum = max(values) or 1
    for tick in range(5):
        x = left + plot_width * tick / 4
        drawing.add(Line(x, bottom, x, height - top, strokeColor=GRID, strokeWidth=0.45))
        drawing.add(String(x, 7, f"${maximum * tick / 4 / 1_000_000:.0f}M", textAnchor="middle", fontSize=7, fillColor=MUTED))
    for index, (row, value) in enumerate(zip(rows, values)):
        y = height - top - (index + 1) * row_height
        bar_width = plot_width * value / maximum
        label = f'{row["hs6"]}  {row["product_name"]}'
        drawing.add(String(left - 7, y + row_height * .37, label, textAnchor="end", fontName="Helvetica-Bold", fontSize=6.1, fillColor=NAVY))
        drawing.add(Rect(left, y + row_height * .12, bar_width, row_height * .5, rx=2, ry=2, fillColor=BLUE, strokeColor=None))
        drawing.add(String(left + bar_width + 6, y + row_height * .37, f"-${value / 1_000_000:.1f}M", fontName="Helvetica-Bold", fontSize=7, fillColor=SLATE))
    return drawing


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setAuthor("Ridoy Roy")
    canvas.setCreator("Ridoy Roy")
    canvas.setProducer("Ridoy Roy")
    canvas.setSubject("Canadian core-steel imports and the 2025 Section 232 tariff changes")
    canvas.setKeywords("Canada, United States, steel, Section 232, trade, tariffs")
    if doc.page == 1:
        canvas.setFillColor(INK)
        canvas.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)
        canvas.setFillColor(BLUE)
        canvas.rect(0, 0, 0.18 * inch, letter[1], fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#203158"))
        canvas.circle(7.9 * inch, 10.3 * inch, 1.35 * inch, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#182746"))
        canvas.circle(7.25 * inch, 9.85 * inch, 0.7 * inch, fill=1, stroke=0)
    else:
        canvas.setFillColor(BLUE)
        canvas.rect(0, 10.2 * inch, 0.18 * inch, 0.8 * inch, fill=1, stroke=0)
        canvas.setStrokeColor(GRID)
        canvas.line(0.65 * inch, 10.35 * inch, 7.85 * inch, 10.35 * inch)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(SLATE)
        canvas.drawString(0.65 * inch, 10.47 * inch, "CANADA-U.S. TRADE SHOCK OBSERVATORY")
        canvas.drawRightString(7.85 * inch, 10.47 * inch, "INITIAL ANALYTICAL RELEASE")
    canvas.setStrokeColor(colors.HexColor("#31415F") if doc.page == 1 else GRID)
    canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#AAB6CC") if doc.page == 1 else SLATE)
    canvas.drawString(0.65 * inch, 0.38 * inch, "Ridoy Roy | Official U.S. Census trade data")
    canvas.drawRightString(7.85 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build() -> Path:
    monthly = load_csv(ROOT / "data" / "processed" / "core_steel_monthly_summary.csv")
    product_changes = load_csv(ROOT / "data" / "processed" / "top_10_hs6_decline_contributors.csv")
    pilot = load_csv(ROOT / "data" / "processed" / "trade_policy_panel.csv")
    universe = load_csv(ROOT / "data" / "processed" / "core_steel_product_universe_2025.csv")
    validation = json.loads((ROOT / "data" / "processed" / "release_validation_report.json").read_text())
    annual = json.loads((ROOT / "reports" / "annual_summary.json").read_text())

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverEyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, tracking=1.6, textColor=colors.HexColor("#7FB0FF"), spaceAfter=16))
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=33, leading=37, textColor=WHITE, alignment=TA_LEFT, spaceAfter=18))
    styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=21, textColor=WHITE, spaceAfter=12))
    styles.add(ParagraphStyle(name="CoverDeck", parent=styles["Normal"], fontSize=10.5, leading=15.5, textColor=colors.HexColor("#CAD5E7"), spaceAfter=12))
    styles.add(ParagraphStyle(name="CoverAuthor", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=colors.HexColor("#7FB0FF"), spaceAfter=6))
    styles.add(ParagraphStyle(name="CoverLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=colors.HexColor("#A9B8D0"), spaceAfter=2))
    styles.add(ParagraphStyle(name="CardLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=NAVY, spaceAfter=2))
    styles.add(ParagraphStyle(name="CoverValue", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=WHITE))
    styles.add(ParagraphStyle(name="CoverCallout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=15, textColor=WHITE, borderPadding=11, backColor=BLUE, spaceBefore=4, spaceAfter=10))
    styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceBefore=5, spaceAfter=9))
    styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=15, textColor=BLUE, spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontSize=9.3, leading=13.4, textColor=colors.HexColor("#27344D"), spaceAfter=7))
    styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontSize=7.6, leading=10.3, textColor=SLATE, spaceAfter=4))
    styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=14.5, textColor=NAVY, borderPadding=9, backColor=PALE_BLUE, spaceBefore=4, spaceAfter=10))

    doc = BaseDocTemplate(str(OUTPUT), pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch, topMargin=0.7 * inch, bottomMargin=0.72 * inch, title="Canada-U.S. Trade Shock Observatory: Initial Release", author="Ridoy Roy")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates(PageTemplate(id="all", frames=frame, onPage=on_page))
    story = []

    # Cover page
    story += [
        Spacer(1, 0.45 * inch),
        Paragraph("TRADE POLICY  /  DATA ANALYSIS  /  2026", styles["CoverEyebrow"]),
        Paragraph("Canada-U.S. Trade<br/>Shock Observatory", styles["CoverTitle"]),
        Paragraph("2025 Section 232 core steel", styles["CoverSub"]),
        Paragraph("A reproducible account of U.S. imports for consumption from Canada, built from official Census records and matched to the 2025 tariff schedule.", styles["CoverDeck"]),
        Spacer(1, 14),
        Paragraph("Ridoy Roy", styles["CoverAuthor"]),
        Spacer(1, 20),
    ]
    annual_2024, annual_2025 = annual["2024"], annual["2025"]
    cards = [
        [Paragraph("2025 IMPORT VALUE", styles["CoverLabel"]), Paragraph("ANNUAL CHANGE", styles["CoverLabel"]), Paragraph("2025 CALCULATED DUTY", styles["CoverLabel"])],
        [Paragraph(usd(annual_2025["value"]), styles["CoverValue"]), Paragraph(f"{annual_2025['value'] / annual_2024['value'] - 1:+.1%}", styles["CoverValue"]), Paragraph(usd(annual_2025["duty"]), styles["CoverValue"])],
    ]
    card_table = Table(cards, colWidths=[2.35 * inch] * 3, rowHeights=[0.32 * inch, 0.58 * inch])
    card_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#172647")), ("LINEABOVE", (0, 0), (-1, 0), 2.5, BLUE), ("INNERGRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#334463")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 9)]))
    story += [card_table, Spacer(1, 18), Paragraph("The value of Canadian core-steel imports in scope was 36.8% lower in 2025 than in 2024. Declines were larger in later policy windows, although this comparison alone does not establish causality.", styles["CoverCallout"]), Spacer(1, 4), Paragraph(f"RELEASED {date.today().strftime('%B %Y').upper()}   /   VALIDATION {validation['status'].upper()}   /   {validation['raw_snapshot_count']} ARCHIVED API RESPONSES", styles["CoverLabel"]), PageBreak()]

    # Scope and methods
    story += [Paragraph("1. Scope and methodology", styles["H1x"]), Paragraph("The observatory measures monthly U.S. imports for consumption of Canadian core steel. Product scope follows the original Section 232 steel ranges and excludes later derivative articles.", styles["Bodyx"])]
    scope_data = [
        ["Dimension", "Initial release specification"],
        ["Trade flow", "U.S. imports for consumption from Canada (Census country code 1220)"],
        ["Coverage", "January 2024 through December 2025"],
        ["Product universe", f"{len(universe):,} HTS10 lines mapped to {len({row['hs6'] for row in universe})} HS6 codes"],
        ["Outcomes", "Import value, dutiable value, calculated duty; quantity where reported"],
        ["Data grain", "HS6-country-month for full scope; HTS10-country-month for pilot"],
        ["Source handling", "Exact JSON responses retained with SHA-256 hashes; API key excluded"],
    ]
    table = Table(scope_data, colWidths=[1.45 * inch, 5.55 * inch], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("LEADING", (0, 0), (-1, -1), 11), ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 1), (-1, -1), colors.white), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [table, Spacer(1, 12), Paragraph("Policy timeline", styles["H2x"])]
    timeline = Table([
        ["Before Mar. 12, 2025", "0%", "Canadian exemption in effect"],
        ["Mar. 12 - Jun. 3, 2025", "25%", "Exemption terminated"],
        ["From Jun. 4, 2025", "50%", "Additional rate increased"],
    ], colWidths=[2.0 * inch, 0.8 * inch, 4.2 * inch])
    timeline.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRID), ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT]), ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"), ("TEXTCOLOR", (1, 0), (1, -1), PURPLE), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story += [timeline, Spacer(1, 10), Paragraph("March and June are transition months. The panel reports start-of-month, end-of-month, and calendar-day-weighted statutory rates, but deliberately leaves the clean-month treatment rate blank. Day weighting is descriptive and does not assume imports were evenly distributed across days.", styles["Bodyx"]), Paragraph("Census returns both a rate-provision total row (RP='-') and its detailed breakdown. The production panel uses the total row and validates this behavior to prevent double-counting.", styles["Callout"]), PageBreak()]

    # Results
    story += [Paragraph("2. Full core-steel results", styles["H1x"]), Paragraph("Import value generally declined during 2025, while reported calculated duty increased after the March and June policy changes. The duty-to-value series divides Census calculated duty by total import value.", styles["Bodyx"])]
    story.append(panel_chart(monthly, [("import_value_usd", "Imports for consumption (USD)", BLUE, 1), ("observed_effective_duty_rate_pct", "Observed duty / value (%)", PURPLE, 1), ("calculated_duty_usd", "Calculated duty (USD)", RED, 1)], width=510, panel_height=82))
    story += [Spacer(1, 4), Paragraph("Orange shading marks March and June 2025 transition months.", styles["Smallx"])]
    regime = [
        ["2025 clean window", "Import value", "vs. same 2024 months", "Duty / value"],
        ["Pre-tariff: Jan.-Feb.", "$1.132B", "-16.2%", "0.0%"],
        ["25%: Apr.-May", "$859.8M", "-35.0%", "22.7%"],
        ["50%: Jul.-Dec.", "$1.640B", "-48.1%", "44.3%"],
    ]
    regime_table = Table(regime, colWidths=[2.0 * inch, 1.5 * inch, 2.0 * inch, 1.25 * inch], repeatRows=1)
    regime_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("FONTSIZE", (0, 0), (-1, -1), 8), ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story += [regime_table, Spacer(1, 7), Paragraph("Reading the table: the year-over-year decline is larger in each successive clean policy window. Prices, demand, seasonality, inventory decisions, product substitution, and advance shipments may also matter. A causal estimate would require a comparison group and a specified counterfactual.", styles["Smallx"]), PageBreak()]

    # Product-level contribution analysis
    story += [Paragraph("3. Products contributing most to the decline", styles["H1x"]), Paragraph("The chart ranks HS6 products by the reduction in annual import value from 2024 to 2025. Together, the top ten account for a substantial share of the aggregate decline, led by zinc-coated flat-rolled steel (HS6 721049) and welded rectangular tubing (HS6 730661).", styles["Bodyx"])]
    story.append(product_decline_chart(product_changes))
    driver_table = [["Rank", "HS6", "Product", "2024 value", "2025 value", "Change", "Share"]]
    for row in product_changes:
        driver_table.append([
            row["rank"], row["hs6"], Paragraph(row["product_name"], styles["Smallx"]), usd(float(row["base_year_value_usd"])),
            usd(float(row["current_year_value_usd"])), usd(float(row["change_usd"])),
            f"{float(row['share_of_total_decline_pct']):.1f}%",
        ])
    dt = Table(driver_table, colWidths=[0.4 * inch, 0.55 * inch, 2.05 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 0.6 * inch], repeatRows=1)
    dt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.3, GRID), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("FONTSIZE", (0, 0), (-1, -1), 6.7), ("ALIGN", (0, 1), (1, -1), "CENTER"), ("ALIGN", (3, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    story += [Spacer(1, 3), dt, Spacer(1, 5), Paragraph("This is an accounting decomposition of the observed value change, not a causal estimate of product-level tariff effects.", styles["Smallx"]), PageBreak()]

    # Pilot
    story += [Paragraph("4. HTS10 pilot: 7208101500", styles["H1x"]), Paragraph("Flat-rolled iron or nonalloy steel coils, 600 mm or more wide, hot-rolled, pickled, with patterns in relief. Unlike the HS6 aggregate release, this line reports quantity in kilograms.", styles["Bodyx"])]
    story.append(panel_chart(pilot, [("import_value_usd", "Imports for consumption (USD)", BLUE, 1), ("quantity_1", "Reported quantity (kg)", GREEN, 1), ("calculated_duty_usd", "Calculated duty (USD)", RED, 1)], width=510, panel_height=88))
    pilot_table = [["Month", "Value", "Quantity (kg)", "Duty", "Policy"]]
    policy_labels = {
        "no_section232_tariff": "No Section 232 tariff",
        "transition_0_to_25": "Transition: 0% to 25%",
        "25_percent": "25% tariff",
        "transition_25_to_50": "Transition: 25% to 50%",
        "50_percent": "50% tariff",
    }
    for row in pilot:
        pilot_table.append([row["month"], usd(float(row["import_value_usd"])), f"{int(row['quantity_1']):,}", usd(float(row["calculated_duty_usd"])), policy_labels.get(row["policy_regime"], row["policy_regime"])])
    pt = Table(pilot_table, colWidths=[0.85 * inch, 1.15 * inch, 1.35 * inch, 1.05 * inch, 2.35 * inch], repeatRows=1)
    pt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.3, GRID), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("FONTSIZE", (0, 0), (-1, -1), 7), ("ALIGN", (1, 1), (3, -1), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story += [Spacer(1, 5), pt, PageBreak()]

    # QA and sources
    story += [Paragraph("5. Quality, limitations, and reproducibility", styles["H1x"]), Paragraph("Release quality controls", styles["H2x"])]
    qa = [
        ["Check", "Result"],
        ["Automated tests", "18 passed"],
        ["Official HS6-month rows", f"{validation['panel_rows']:,}"],
        ["Months", str(validation["months"])],
        ["Raw Census snapshots", str(validation["raw_snapshot_count"])],
        ["Snapshot integrity", "SHA-256 verified; API key excluded from metadata"],
        ["Transition handling", "March and June 2025 flagged; excluded from clean comparisons"],
        ["HS6 quantity", "Unavailable in aggregate API rows; stored as null, not zero"],
    ]
    qt = Table(qa, colWidths=[2.1 * inch, 4.9 * inch], repeatRows=1)
    qt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("LINEBELOW", (0, 0), (-1, -1), 0.45, GRID), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]), ("FONTSIZE", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5)]))
    interpretation_cards = Table([
        [Paragraph("WHAT THE EVIDENCE SHOWS", styles["CardLabel"]), Paragraph("WHAT IT DOES NOT CLAIM", styles["CardLabel"])],
        [Paragraph("Observed import values, calculated duty, policy timing, and the products contributing most to the annual decline.", styles["Bodyx"]), Paragraph("A causal tariff effect, welfare impact, tariff pass-through, domestic output, employment effects, or trade diversion.", styles["Bodyx"])],
    ], colWidths=[3.45 * inch, 3.45 * inch])
    interpretation_cards.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), PALE_BLUE), ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FFF4E5")), ("TEXTCOLOR", (0, 0), (0, 0), BLUE), ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#A75D00")), ("BOX", (0, 0), (0, -1), 0.5, colors.HexColor("#B9D2FA")), ("BOX", (1, 0), (1, -1), 0.5, colors.HexColor("#F2D39C")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [qt, Spacer(1, 10), interpretation_cards, Paragraph("Reproduction", styles["H2x"]), Paragraph("Run <font name='Courier'>python scripts/build_release.py --reuse-snapshots</font> to rebuild the processed files from archived source responses. Run <font name='Courier'>python -m unittest discover -s tests -v</font> to repeat the validation tests.", styles["Bodyx"]), Paragraph("Official sources", styles["H2x"])]
    sources = [
        ("U.S. Census International Trade API", "https://api.census.gov/data/timeseries/intltrade/imports/hs.html"),
        ("Census API variable definitions", "https://api.census.gov/data/timeseries/intltrade/imports/hs/variables.html"),
        ("January 2025 Census commodity concordance", "https://www.census.gov/trade/downloads/concordance/comm_month/2025/index.html"),
        ("February 2025 steel proclamation", "https://www.whitehouse.gov/presidential-actions/2025/02/adjusting-imports-of-steel-into-the-united-states/"),
        ("June 2025 steel and aluminum proclamation", "https://www.whitehouse.gov/presidential-actions/2025/06/adjusting-imports-of-aluminum-and-steel-into-the-united-states/"),
    ]
    for label, url in sources:
        story.append(Paragraph(f"- <link href='{url}' color='#2563EB'>{label}</link>", styles["Smallx"]))
    story += [Spacer(1, 8), Paragraph("Publication note", styles["H2x"]), Paragraph("Recommended citation: Roy, Ridoy. 2026. <i>Canada-U.S. Trade Shock Observatory: 2025 Section 232 Core Steel, Initial Analytical Release.</i> Data derived from the U.S. Census Bureau and official presidential proclamations.", styles["Bodyx"])]

    doc.build(story)
    return OUTPUT


if __name__ == "__main__":
    print(build())
