# Canada-U.S. Trade Shock Observatory

[![Tests](https://github.com/ridoy-roy/canada-us-trade-shock-observatory/actions/workflows/tests.yml/badge.svg)](https://github.com/ridoy-roy/canada-us-trade-shock-observatory/actions/workflows/tests.yml)

**Ridoy Roy | Data Analyst**

**Independent Portfolio Project**

## Overview

This project examines how U.S. imports of Canadian core-steel products changed
around the 2025 Section 232 tariff increases. It combines official monthly U.S.
Census trade records with a date-specific tariff history, harmonizes HTS10
products to HS6, and produces a validated analytical panel, charts, and a
six-page report.

The analysis is descriptive. It documents trade patterns before and after the
policy changes without claiming that tariffs alone caused those changes.

## Key findings

- Import value in the defined core-steel scope declined from **$7.13 billion in
  2024 to $4.51 billion in 2025**, a decrease of **36.8%**.
- Census calculated duty increased from **$0 in 2024 to $1.07 billion in
  2025**.
- Year-over-year import declines were larger in the later clean policy windows:
  **-16.2%** in January-February, **-35.0%** in April-May, and **-48.1%** in
  July-December.
- Zinc-coated flat-rolled steel (HS6 **721049**) and welded rectangular steel
  tube (HS6 **730661**) made the largest individual contributions to the
  annual decline.
- The ten largest product-level contributors accounted for approximately
  **51.0%** of the aggregate decrease.

![Monthly Canadian core-steel import value and calculated duty](artifacts/core_steel_2024_2025_monthly.svg)

## Project outputs

- **[Read the six-page analytical report](output/pdf/canada_us_trade_shock_observatory_v0.pdf)**
- [Explore the analysis notebook](notebooks/initial_release_walkthrough.ipynb)
- [Review the detailed analytical report](reports/v0_release_report.md)
- [Open the validated monthly summary](data/processed/core_steel_monthly_summary.csv)
- [Explore the top-ten product contribution table](data/processed/top_10_hs6_decline_contributors.csv)
- [Review the release validation results](data/processed/release_validation_report.json)

## Analytical scope

| Dimension | Coverage |
|---|---|
| Trade flow | U.S. imports for consumption from Canada |
| Country code | Census code 1220 |
| Period | January 2024-December 2025 |
| Product scope | Original Section 232 core-steel HS6 ranges |
| Product universe | 746 HTS10 lines mapped to 168 HS6 codes |
| Observed products | 164 HS6 codes with reported trade |
| Main outcomes | Import value, dutiable value, calculated duty |
| Pilot product | HTS10 7208101500, including reported quantity |

Later derivative articles are outside the current product scope.

## Policy timeline

| Entry date | Additional Section 232 rate |
|---|---:|
| Before March 12, 2025 | 0% |
| March 12-June 3, 2025 | 25% |
| From June 4, 2025 | 50% |

March and June are treated as transition months because the tariff changed
partway through each month. They are flagged in the panel and excluded from
clean full-month comparisons. The panel also reports a calendar-day-weighted
statutory rate for descriptive use.

## Methodology

1. Retrieve official Census imports-for-consumption records for Canada.
2. Preserve exact source responses locally as content-addressed snapshots.
3. Select Census total rows to avoid double-counting rate-provision details.
4. Map HTS10 products to HS6 and apply the encoded core-steel scope.
5. Attach the tariff regime and identify transition months.
6. Validate coverage, keys, measures, product scope, and policy flags.
7. Produce monthly summaries, product contributions, charts, and reports.

The observed duty-to-value ratio is calculated as Census calculated duty
divided by imports for consumption. It is not expected to equal the headline
Section 232 rate because entry treatment, timing, exclusions, programs, and
ordinary duties can differ.

## Data quality

The release contains **3,694 HS6-month observations** across 24 months and
passes **18 automated tests**. Validation checks cover:

- missing months and duplicate panel keys;
- malformed Census responses and negative measures;
- non-Canadian or out-of-scope observations;
- inconsistent quantity units;
- rate-provision aggregation; and
- March and June transition-month treatment.

Raw API snapshots, credentials, local environments, and temporary files are
excluded from Git. Credentials are supplied through environment variables and
are never written to snapshot metadata. Aggregate HS6 quantity is reported as
unavailable rather than incorrectly recorded as zero.

## Reproducing the analysis

The core pipeline uses Python 3.11+ and the standard library.

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    $env:PYTHONPATH = "$PWD\src"
    $env:CENSUS_API_KEY = "your Census API key"
    python scripts/build_release.py
    python -m unittest discover -s tests -v

Request a key from the
[U.S. Census API key page](https://api.census.gov/data/key_signup.html).
Notebook dependencies can be installed with:

    python -m pip install -e ".[analysis]"

An offline fixture build is available for testing the ingestion contract:

    python scripts/build_v0_panel.py --source fixture

Fixture values are synthetic and must not be interpreted as observed trade
data.

## Repository structure

    config/          Policy history and product-scope definitions
    data/processed/  Validated analytical datasets
    artifacts/       Publication-ready charts
    notebooks/       Executed analytical walkthrough
    reports/         Analytical summary and portfolio material
    src/             Reusable ingestion and transformation code
    tests/           Automated tests and synthetic fixtures
    output/pdf/      Final analytical report

## Interpretation

The results are an accounting description of observed trade values. They do
not estimate welfare effects, tariff pass-through, domestic production,
employment effects, or a causal treatment effect. Prices, demand, seasonality,
inventory timing, product substitution, and advance shipments may also
influence the observed changes.

## Official sources

- [U.S. Census monthly imports by HS API](https://api.census.gov/data/timeseries/intltrade/imports/hs.html)
- [Census API variable definitions](https://api.census.gov/data/timeseries/intltrade/imports/hs/variables.html)
- [Census Schedule C country codes](https://www.census.gov/foreign-trade/schedules/c/countrycodes.html)
- [February 2025 steel proclamation](https://www.whitehouse.gov/presidential-actions/2025/02/adjusting-imports-of-steel-into-the-united-states/)
- [June 2025 steel and aluminum proclamation](https://www.whitehouse.gov/presidential-actions/2025/06/adjusting-imports-of-aluminum-and-steel-into-the-united-states/)

## Future extensions

- Add comparison countries and products for a formal causal design.
- Verify treatment at the Chapter 99 entry level.
- Extend the panel across additional HTS vintages.

## Author

**Ridoy Roy — Data Analyst**

[LinkedIn](https://www.linkedin.com/in/royridoy)

This portfolio project demonstrates data ingestion, quality assurance,
policy-date modeling, product-code harmonization, visualization, and clear
analytical communication.
