# Publishing guide

The recommended release format is a public GitHub repository plus the included
PDF report.

## Publish with the GitHub website

1. Create a new **public** repository named
   `canada-us-trade-shock-observatory`. Do not initialize it with a README.
2. Upload this project folder, excluding anything already covered by
   `.gitignore`.
3. Confirm that `.env`, `data/raw/`, `sources/`, `.venv/`, and `tmp/` are absent
   before committing.
4. Use the commit message `Initial release: 2025 Section 232 core steel`.
5. Create a GitHub release tagged `v0.1.0` and attach
   `output/pdf/canada_us_trade_shock_observatory_v0.pdf`.

Suggested repository description:

> Reproducible U.S. Census analysis of the 2025 Section 232 tariff shock to
> Canadian core-steel imports, with policy timing, validation, data, and report.

## Release checklist

- All automated tests pass.
- `release_validation_report.json` reports `passed`.
- The PDF opens and all five pages render correctly.
- No API key or raw response is present in the files to be uploaded.
- Results are described as observational, not causal.
