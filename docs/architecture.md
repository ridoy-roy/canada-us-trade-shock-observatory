# Initial release architecture

```text
Official Census HS imports API + commodity concordance
        |
        v
exact JSON + metadata (immutable, SHA-256 addressed)
        |
        +---- release manifest pins exact source and configuration hashes
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
        +---- validated HS6 and HTS10 panels
        +---- charts and analytical reports
        +---- output hashes recorded in release_manifest.json
```

The modules separate acquisition (`census.py`), product identity
(`harmonize.py`), legal timing (`policy.py`), aggregation (`panel.py`), checks
(`validate.py`), provenance (`provenance.py`), and presentation (`chart.py`).
The production build downloads a missing official commodity concordance and
archives it by content hash. A fresh build retrieves current official data; an
exact rebuild resolves only the files pinned in the release manifest and fails
on any missing file or hash mismatch. This keeps future dashboard work
downstream of the auditable data contract.
