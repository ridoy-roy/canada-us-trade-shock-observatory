# Initial release data dictionary

The output grain is one `month × HTS10 × country` observation after summing
Census rate-provision rows. The country is always Canada (`1220`).

| Field | Meaning |
|---|---|
| `month`, `period_start` | Statistical month and its first calendar date |
| `hts10`, `hs6` | Normalized 2025 HTS10 and six-digit prefix |
| `hts_vintage` | Classification vintage, fixed to 2025 in the initial release |
| `hs6_harmonization_method` | Initial mapping method (`prefix`) |
| `concordance_status` | Warning that cross-vintage concordance remains future work |
| `is_section232_core_steel` | Membership in the encoded Proclamation 9705 core ranges |
| `core_steel_range_note` | Matching source-range description |
| `country_code`, `country_name` | Census origin-country identifiers |
| `hts10_description` | Census long commodity description |
| `import_value_usd` | Imports for consumption, total value (`CON_VAL_MO`) |
| `quantity_1`, `quantity_unit` | First imports-for-consumption quantity and Census unit |
| `dutiable_value_usd` | Imports for consumption, dutiable value (`DUT_VAL_MO`) |
| `calculated_duty_usd` | Imports for consumption, calculated duty (`CAL_DUT_MO`) |
| `observed_effective_duty_rate` | Calculated duty divided by import value; not a pure Section 232 rate |
| `rate_provisions` | Pipe-delimited Census rate-provision codes aggregated into the row |
| `source_row_count` | Number of Census rows aggregated |
| `source_last_update` | Census last-update value |
| `data_status` | `official_census_api` or `contract_fixture_not_observed` |
| `section232_rate_month_start` | Statutory additional rate on first day |
| `section232_rate_month_end` | Statutory additional rate on last day |
| `section232_rate_day_weighted` | Calendar-day-weighted descriptive rate |
| `section232_rate_clean_month` | Uniform rate, null when the rate changed within month |
| `policy_regime` | Human-readable monthly regime label |
| `is_transition_month` | True for March and June 2025 |
| `include_clean_month_analysis` | False for transition months |

## Assumptions and boundaries

- Product membership is based on the core steel HS6 ranges, then applied to
  HTS10 lines through their six-digit prefix. Derivative steel is excluded.
- A monthly observation cannot reveal entry-day composition. The day-weighted
  statutory rate is descriptive and is not used as a measured effective rate.
- `CON_QY1_MO` is only comparable through time when `UNIT_QY1` is stable; the
  validator enforces that stability within each HTS10 build.
- Census may revise data. Every distinct API response is retained as a new
  content-addressed snapshot, so the processed panel can be tied to raw bytes.
