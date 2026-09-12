# Publishing guide

When the project is ready to be made public, the recommended release format is
a GitHub repository plus the included PDF report. Keep the repository private
until the publication decision is made.

## Publish the existing GitHub repository

1. Open the repository settings and review the visibility-change warning.
2. Confirm that `.env`, `data/raw/`, `sources/`, `.venv/`, and `tmp/` are absent
   from the GitHub file list.
3. Change the existing repository from private to public only when the launch
   post is ready.
4. Create a GitHub release tagged `v0.1.0` and attach
   `output/pdf/canada_us_trade_shock_observatory_v0.pdf`.
5. Open the public repository in a signed-out browser and verify the README,
   chart, report link, and test badge.

Suggested repository description:

> Reproducible U.S. Census analysis of the 2025 Section 232 tariff shock to
> Canadian core-steel imports, with policy timing, validation, data, and report.

## Release checklist

- All 23 automated tests pass, including the offline end-to-end build.
- `python scripts/verify_release.py` confirms the committed release hashes.
- `release_validation_report.json` reports `passed`.
- The PDF opens and all six pages render correctly.
- No API key or raw response is present in the files to be uploaded.
- Results are described as observational, not causal.
