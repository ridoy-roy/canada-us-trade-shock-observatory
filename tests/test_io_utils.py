import csv
import tempfile
import unittest
from pathlib import Path

from trade_shock.io_utils import write_dict_rows_csv, write_text_lf


class PortableOutputTests(unittest.TestCase):
    def test_text_writer_uses_lf_endings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            write_text_lf(path, "one\ntwo\n")
            self.assertEqual(path.read_bytes(), b"one\ntwo\n")

    def test_csv_writer_uses_lf_endings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.csv"
            write_dict_rows_csv([{"code": "720810", "name": "steel"}], path)
            self.assertNotIn(b"\r", path.read_bytes())
            with path.open(encoding="utf-8", newline="") as handle:
                self.assertEqual(
                    list(csv.DictReader(handle)),
                    [{"code": "720810", "name": "steel"}],
                )


if __name__ == "__main__":
    unittest.main()
