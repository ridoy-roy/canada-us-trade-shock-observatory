# Initial release architecture

```text
Official Census HS imports API
        |
        v
exact JSON + metadata (immutable, SHA-256 addressed)
        |
        v
parse and aggregate rate-provision rows
        |
        +---- HTS10 -> HS6 -> core-steel range membership
        |
        +---- daily policy history -> monthly transition fields
        |
        v
validation gate
        |
        +---- trade_policy_panel.csv
        +---- validation_report.json
        +---- pilot monthly SVG chart
```

The modules separate acquisition (`census.py`), product identity
(`harmonize.py`), legal timing (`policy.py`), aggregation (`panel.py`), checks
(`validate.py`), and presentation (`chart.py`). This keeps future dashboard work
downstream of the auditable data contract.
