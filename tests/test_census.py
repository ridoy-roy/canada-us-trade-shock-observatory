import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from trade_shock.census import CensusError, FIELDS, parse_api_payload, write_immutable_snapshot


class CensusTests(unittest.TestCase):
    def test_parses_row_array(self):
        values = ["x"] * len(FIELDS)
        payload = json.dumps([list(FIELDS), values]).encode()
        self.assertEqual(parse_api_payload(payload)[0]["I_COMMODITY"], "x")

    def test_missing_columns_fail(self):
        with self.assertRaises(CensusError):
            parse_api_payload(b'[["I_COMMODITY"],["7208101500"]]')

    def test_identical_predicate_duplicates_are_accepted(self):
        header = [*FIELDS, "I_COMMODITY", "CTY_CODE"]
        base = {field: "x" for field in FIELDS}
        base["I_COMMODITY"] = "7208101500"
        base["CTY_CODE"] = "1220"
        values = [base[field] for field in FIELDS] + ["7208101500", "1220"]
        rows = parse_api_payload(json.dumps([header, values]).encode())
        self.assertEqual(rows[0]["I_COMMODITY"], "7208101500")

    def test_conflicting_predicate_duplicates_fail(self):
        header = [*FIELDS, "I_COMMODITY"]
        values = ["x"] * len(FIELDS) + ["different"]
        with self.assertRaises(CensusError):
            parse_api_payload(json.dumps([header, values]).encode())

    def test_snapshot_is_content_addressed_and_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = b'[["a"],["b"]]'
            first = write_immutable_snapshot(payload, Path(folder), "2025-01", "7208101500", {})
            second = write_immutable_snapshot(payload, Path(folder), "2025-01", "7208101500", {})
            self.assertEqual(first.data_path, second.data_path)
            self.assertEqual(first.sha256, hashlib.sha256(payload).hexdigest())
            self.assertEqual(first.data_path.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
