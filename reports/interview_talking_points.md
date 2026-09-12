# Interview talking points

## 60-second project explanation

I built the Canada-U.S. Trade Shock Observatory to study how U.S. imports of
Canadian core-steel products changed around the 2025 Section 232 tariff
increases. I used the official U.S. Census trade API and created a Python
pipeline covering 2024 and 2025. The workflow maps product codes, handles the
March and June policy transition months, validates the data, and produces a
monthly analytical panel and report. The main descriptive finding was that
import value in the defined scope decreased by 36.8% in 2025, while Census
calculated duty reached $1.07 billion. I was careful not to present that as a
causal estimate because other factors could also explain part of the change.

## If asked what was technically difficult

The main challenge was preventing incorrect aggregation. Census provides total
rows and rate-provision detail, so summing everything would double-count trade.
I built validation around the total-row selection, checked unique product-month
keys, and treated unavailable aggregate quantity as missing rather than zero.

## If asked how quality was controlled

The project uses immutable, content-addressed source snapshots and a release
manifest containing SHA-256 hashes. Twenty-three automated tests cover policy
dates, transition months, product scope, Census response parsing, aggregation,
tamper detection, and a complete offline release build.

## If asked what the result means

The result shows a substantial observed decline in the selected Canadian steel
imports during 2025, with larger year-over-year declines in later clean policy
windows. It does not prove that the tariffs alone caused the decline. A stronger
causal study would add comparison products or countries and define a formal
counterfactual.

## If asked what you would improve next

I would add a comparison group, verify tariff treatment using Chapter 99 entry
data, and extend the analysis across additional HTS vintages. That would move
the project from a descriptive observatory toward a causal research design.
