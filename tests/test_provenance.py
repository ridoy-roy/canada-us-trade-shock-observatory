import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from trade_shock.provenance import (
    resolve_manifest_sources,
    verify_release_manifest,
    write_release_manifest,
)
from trade_shock.universe import ensure_commodity_concordance


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class ProvenanceTests(unittest.TestCase):
    def _root(self, folder):
        root = Path(folder)
        (root / "config").mkdir()
        (root / "config" / "core_steel_hs6_ranges.csv").write_text("a,b\n", encoding="utf-8")
        (root / "config" / "policy_history.csv").write_text("a,b\n", encoding="utf-8")
        return root

    def test_manifest_pins_one_snapshot_when_an_extra_revision_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self._root(folder)
            source = root / "data" / "raw" / "census_imports_hs" / "2025-01"
            source.mkdir(parents=True)
            pinned = source / "hs6-720star-one.json"
            pinned.write_bytes(b"pinned")
            (source / "hs6-720star-later.json").write_bytes(b"later")
            concordance = root / "data" / "raw" / "usitc_hts" / "source.zip"
            concordance.parent.mkdir(parents=True)
            concordance.write_bytes(b"zip")
            manifest = write_release_manifest(
                root, root / "manifest.json", ["2025-01"], ("720",),
                [{"month": "2025-01", "prefix": "720", "path": str(pinned)}],
                concordance, [],
            )
            _, snapshots = resolve_manifest_sources(root, manifest, ["2025-01"], ("720",))
            self.assertEqual(Path(snapshots[0]["path"]), pinned)

    def test_manifest_detects_source_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self._root(folder)
            snapshot = root / "snapshot.json"
            concordance = root / "source.zip"
            snapshot.write_bytes(b"original")
            concordance.write_bytes(b"zip")
            manifest = write_release_manifest(
                root, root / "manifest.json", ["2025-01"], ("720",),
                [{"month": "2025-01", "prefix": "720", "path": str(snapshot)}],
                concordance, [],
            )
            snapshot.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                resolve_manifest_sources(root, manifest, ["2025-01"], ("720",))

    def test_concordance_download_is_content_addressed(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as bundle:
            bundle.writestr("CONCORD.TXT", "record")
        payload = stream.getvalue()
        with tempfile.TemporaryDirectory() as folder:
            archive = ensure_commodity_concordance(
                Path(folder), opener=lambda *args, **kwargs: _Response(payload)
            )
            self.assertIn(hashlib.sha256(payload).hexdigest()[:16], archive.name)
            self.assertEqual(archive.read_bytes(), payload)
            self.assertTrue(archive.with_suffix(".metadata.json").is_file())

    def test_public_release_files_can_be_verified_without_raw_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self._root(folder)
            snapshot = root / "raw.json"
            concordance = root / "source.zip"
            output = root / "result.csv"
            snapshot.write_bytes(b"raw")
            concordance.write_bytes(b"zip")
            output.write_bytes(b"result")
            manifest = write_release_manifest(
                root, root / "manifest.json", ["2025-01"], ("720",),
                [{"month": "2025-01", "prefix": "720", "path": str(snapshot)}],
                concordance, [output],
            )
            snapshot.unlink()
            concordance.unlink()
            result = verify_release_manifest(root, manifest)
            self.assertEqual(result["verified_release_files"], 3)
            self.assertEqual(result["verified_source_files"], 0)


if __name__ == "__main__":
    unittest.main()
