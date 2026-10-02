"""Tests for envforge.store module."""
import json
import os
import unittest
from pathlib import Path
from tests.helpers import TempStore, make_sample_profile
from envforge.store import Store


class TestStoreInit(unittest.TestCase):
    def test_init_creates_directories(self):
        with TempStore() as ts:
            self.assertTrue(ts.store.profiles_dir.exists())
            self.assertTrue(ts.store.history_dir.exists())

    def test_init_creates_meta(self):
        with TempStore() as ts:
            meta_path = ts.store.root / "meta.json"
            self.assertTrue(meta_path.exists())
            meta = json.loads(meta_path.read_text())
            self.assertIn("profiles", meta)
            self.assertEqual(meta["profiles"], [])

    def test_is_initialized(self):
        with TempStore() as ts:
            self.assertTrue(ts.store.is_initialized())

    def test_not_initialized_before_init(self):
        import tempfile
        d = tempfile.mkdtemp()
        store = Store(d)
        self.assertFalse(store.is_initialized())
        import shutil
        shutil.rmtree(d, ignore_errors=True)


class TestStoreSaveGet(unittest.TestCase):
    def test_save_and_get(self):
        with TempStore() as ts:
            profile = make_sample_profile("save-test")
            ts.store.save(profile)
            loaded = ts.store.get("save-test")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["name"], "save-test")
            self.assertEqual(loaded["os"]["system"], "Linux")

    def test_get_nonexistent_returns_none(self):
        with TempStore() as ts:
            self.assertIsNone(ts.store.get("does-not-exist"))

    def test_save_updates_meta(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("profile-a"))
            ts.store.save(make_sample_profile("profile-b"))
            meta = json.loads((ts.store.root / "meta.json").read_text())
            self.assertIn("profile-a", meta["profiles"])
            self.assertIn("profile-b", meta["profiles"])

    def test_save_creates_history(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("hist-test"))
            hist_dir = ts.store.history_dir / "hist-test"
            self.assertTrue(hist_dir.exists())
            snapshots = list(hist_dir.glob("*.json"))
            self.assertEqual(len(snapshots), 1)


class TestStoreList(unittest.TestCase):
    def test_list_empty(self):
        with TempStore() as ts:
            self.assertEqual(ts.store.list_profiles(), [])

    def test_list_profiles(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("alpha"))
            ts.store.save(make_sample_profile("beta"))
            names = ts.store.list_profiles()
            self.assertEqual(names, ["alpha", "beta"])

    def test_list_all_with_summaries(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("gamma"))
            all_profiles = ts.store.list_all()
            self.assertEqual(len(all_profiles), 1)
            self.assertEqual(all_profiles[0]["name"], "gamma")


class TestStoreDelete(unittest.TestCase):
    def test_delete_existing(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("to-delete"))
            self.assertTrue(ts.store.delete("to-delete"))
            self.assertIsNone(ts.store.get("to-delete"))

    def test_delete_nonexistent(self):
        with TempStore() as ts:
            self.assertFalse(ts.store.delete("nope"))

    def test_delete_removes_from_meta(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("rem-me"))
            ts.store.delete("rem-me")
            meta = json.loads((ts.store.root / "meta.json").read_text())
            self.assertNotIn("rem-me", meta["profiles"])


class TestStoreHistory(unittest.TestCase):
    def test_history_for_profile(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("hist-prof"))
            history = ts.store.history("hist-prof")
            self.assertEqual(len(history), 1)
            self.assertIn("timestamp", history[0])
            self.assertIn("tools", history[0])

    def test_history_empty_for_unknown(self):
        with TempStore() as ts:
            self.assertEqual(ts.store.history("unknown"), [])


class TestStoreStats(unittest.TestCase):
    def test_stats_empty(self):
        with TempStore() as ts:
            stats = ts.store.stats()
            self.assertEqual(stats["profiles"], 0)
            self.assertEqual(stats["history_snapshots"], 0)

    def test_stats_with_profiles(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("s1"))
            ts.store.save(make_sample_profile("s2"))
            stats = ts.store.stats()
            self.assertEqual(stats["profiles"], 2)
            self.assertEqual(stats["history_snapshots"], 2)


class TestStoreExportImport(unittest.TestCase):
    def test_export_creates_file(self):
        import tempfile
        with TempStore() as ts:
            ts.store.save(make_sample_profile("export-me"))
            out = os.path.join(tempfile.gettempdir(), "envforge_test_export.json")
            self.assertTrue(ts.store.export_profile("export-me", out))
            self.assertTrue(os.path.exists(out))
            data = json.loads(Path(out).read_text())
            self.assertEqual(data["name"], "export-me")
            os.unlink(out)

    def test_export_nonexistent_returns_false(self):
        with TempStore() as ts:
            self.assertFalse(ts.store.export_profile("nope", "/tmp/x.json"))

    def test_import_profile(self):
        import tempfile
        with TempStore() as ts:
            profile = make_sample_profile("imported")
            path = os.path.join(tempfile.gettempdir(), "envforge_test_import.json")
            Path(path).write_text(json.dumps(profile))
            result = ts.store.import_profile(path)
            self.assertEqual(result["name"], "imported")
            loaded = ts.store.get("imported")
            self.assertIsNotNone(loaded)
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
