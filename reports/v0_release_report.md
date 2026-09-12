# Canada-U.S. Trade Shock Observatory: Initial Analytical Release

**Ridoy Roy | Data Analyst**

**Independent Portfolio Project**

## Release status

- Validation: **passed**
- Official Census observations: **3,694** HS6-month rows
- Coverage: **24 months**, January 2024–December 2025
- Product universe: **746 HTS10 lines** mapping to **168 HS6 codes**
- Policy transitions: March 12 and June 4, 2025; both transition months are flagged and excluded from clean-month comparisons.

## Descriptive results

| Year | Import value | Calculated duty |
|---|---:|---:|
| 2024 | $7,134,857,615 | $0 |
| 2025 | $4,506,162,362 | $1,070,086,289 |

The value of imports in scope was **36.8% lower** in 2025 than in 2024. This comparison is descriptive. Census calculated duty can include duties beyond Section 232, so it should not be read as a stand-alone measure of the steel tariff.

### Clean-month regime comparison

| 2025 regime window | Import value | Change from same 2024 months | Observed duty/value |
|---|---:|---:|---:|
| Pre-tariff clean months | $1,132,248,200 | -16.2% | 0.0% |
| 25% clean months | $859,830,323 | -35.0% | 22.7% |
| 50% clean months | $1,639,758,514 | -48.1% | 44.3% |

The year-over-year decline is larger in each successive window. The reported duty-to-value ratio remains below the headline statutory rate because entries can differ in treatment and timing, and because other provisions may apply. March and June are left out of this comparison because the tariff changed during those months.

## Products contributing most to the decline

| Rank | HS6 | Product | 2024 value | 2025 value | Change | Share of aggregate decline |
|---:|---:|---|---:|---:|---:|---:|
| 1 | 721049 | Zinc-coated flat-rolled steel | $817,275,018 | $536,570,556 | -$280,704,462 | 10.7% |
| 2 | 730661 | Welded rectangular steel tube | $447,899,317 | $235,107,810 | -$212,791,507 | 8.1% |
| 3 | 720837 | Hot-rolled coil, 4.75-10 mm | $241,700,626 | $115,346,809 | -$126,353,817 | 4.8% |
| 4 | 722530 | Hot-rolled alloy-steel coil | $233,167,321 | $107,989,534 | -$125,177,787 | 4.8% |
| 5 | 720838 | Hot-rolled coil, 3-4.75 mm | $222,897,410 | $107,924,060 | -$114,973,350 | 4.4% |
| 6 | 720917 | Cold-rolled coil, 0.5-1 mm | $214,103,254 | $114,499,608 | -$99,603,646 | 3.8% |
| 7 | 721391 | Hot-rolled bars/rods, under 14 mm | $300,473,574 | $201,197,321 | -$99,276,253 | 3.8% |
| 8 | 720839 | Hot-rolled coil, under 3 mm | $181,406,980 | $85,297,457 | -$96,109,523 | 3.7% |
| 9 | 720916 | Cold-rolled coil, 1-3 mm | $219,426,085 | $124,338,041 | -$95,088,044 | 3.6% |
| 10 | 720712 | Semifinished rectangular steel | $171,668,068 | $80,909,142 | -$90,758,926 | 3.5% |

The ranking is an accounting decomposition of the value change, not an estimate of each product's causal response to the tariff.

## Interpretation boundaries

- The product universe is the January 2025 Census import concordance filtered to the Proclamation 9705 core steel HS6 ranges; derivative articles are excluded.
- Trade data are imports for consumption from Canada (`CTY_CODE=1220`) and use Census `RP="-"` total rows to avoid double-counting rate-provision breakdowns.
- Census does not report quantity for the HS6 aggregate rows (`UNIT_QY1="-"`), so full-scope quantity is recorded as unavailable rather than as zero. The HTS10 pilot panel retains its reported kilogram quantity series.
- HTS10 lines are mapped to HS6 by prefix. Cross-vintage identity remains explicit through the `hts_vintage` field.
- March and June 2025 contain within-month policy changes. Their day-weighted policy rates are descriptive only.
- No causal claim is made without a control group and a formally specified counterfactual design.
