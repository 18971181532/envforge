"""Tests for envforge.cli module."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from tests.helpers import TempStore, run_cli, make_sample_profile
from envforge.store import Store


class TestCLIInit(unittest.TestCase):
    def test_init_creates_store(self):
        d = tempfile.mkdtemp()
        try:
            code, out, _ = run_cli("-C", d, "init")
            self.assertEqual(code, 0)
            self.assertIn("Initialized", out)
            self.assertTrue(os.path.exists(os.path.join(d, ".envforge")))
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


class TestCLICapture(unittest.TestCase):
    def test_capture_creates_profile(self):
        with TempStore() as ts:
            code, out, _ = run_cli("-C", ts.dir, "capture", "test-capture", "--no-packages")
            self.assertEqual(code, 0)
            self.assertIn("Saved", out)
            profile = ts.store.get("test-capture")
            self.assertIsNotNone(profile)

    def test_capture_auto_name(self):
        with TempStore() as ts:
            code, out, _ = run_cli("-C", ts.dir, "capture", "--no-packages")
            self.assertEqual(code, 0)
            names = ts.store.list_profiles()
            self.assertEqual(len(names), 1)
            self.assertTrue(names[0].startswith("capture_"))


class TestCLIList(unittest.TestCase):
    def test_list_empty(self):
        with TempStore() as ts:
            code, out, _ = run_cli("-C", ts.dir, "list")
            self.assertEqual(code, 0)
            self.assertIn("No profiles", out)

    def test_list_with_profiles(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("list-test"))
            code, out, _ = run_cli("-C", ts.dir, "list")
            self.assertEqual(code, 0)
            self.assertIn("list-test", out)


class TestCLIShow(unittest.TestCase):
    def test_show_existing(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("show-test"))
            code, out, _ = run_cli("-C", ts.dir, "show", "show-test")
            self.assertEqual(code, 0)
            self.assertIn("show-test", out)
            self.assertIn("Tools", out)

    def test_show_nonexistent(self):
        with TempStore() as ts:
            code, out, err = run_cli("-C", ts.dir, "show", "nope")
            self.assertEqual(code, 1)
            self.assertIn("not found", err)

    def test_show_json(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("json-test"))
            code, out, _ = run_cli("-C", ts.dir, "show", "json-test", "--json")
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["name"], "json-test")


class TestCLIDiff(unittest.TestCase):
    def test_diff_runs(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("diff-test"))
            code, out, _ = run_cli("-C", ts.dir, "diff", "diff-test")
            self.assertEqual(code, 0)
            self.assertIn("Drift report", out)

    def test_diff_nonexistent(self):
        with TempStore() as ts:
            code, out, err = run_cli("-C", ts.dir, "diff", "nope")
            self.assertEqual(code, 1)


class TestCLICompare(unittest.TestCase):
    def test_compare_two_profiles(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("cmp-a"))
            ts.store.save(make_sample_profile("cmp-b"))
            code, out, _ = run_cli("-C", ts.dir, "compare", "cmp-a", "cmp-b")
            self.assertEqual(code, 0)
            self.assertIn("Comparison", out)

    def test_compare_nonexistent(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("exists"))
            code, out, err = run_cli("-C", ts.dir, "compare", "exists", "nope")
            self.assertEqual(code, 1)


class TestCLIBootstrap(unittest.TestCase):
    def test_bootstrap_generates_file(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("boot-test"))
            out_file = os.path.join(ts.dir, "bootstrap.sh")
            code, out, _ = run_cli("-C", ts.dir, "bootstrap", "boot-test",
                                     "--shell", "bash", "--output", out_file)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(out_file))
            content = Path(out_file).read_text()
            self.assertIn("#!/usr/bin/env bash", content)

    def test_bootstrap_nonexistent(self):
        with TempStore() as ts:
            code, out, err = run_cli("-C", ts.dir, "bootstrap", "nope")
            self.assertEqual(code, 1)


class TestCLIDelete(unittest.TestCase):
    def test_delete_existing(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("del-test"))
            code, out, _ = run_cli("-C", ts.dir, "delete", "del-test")
            self.assertEqual(code, 0)
            self.assertIn("Deleted", out)
            self.assertIsNone(ts.store.get("del-test"))

    def test_delete_nonexistent(self):
        with TempStore() as ts:
            code, out, err = run_cli("-C", ts.dir, "delete", "nope")
            self.assertEqual(code, 1)


class TestCLIHistory(unittest.TestCase):
    def test_history(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("hist-test"))
            code, out, _ = run_cli("-C", ts.dir, "history", "hist-test")
            self.assertEqual(code, 0)
            self.assertIn("History", out)


class TestCLIStats(unittest.TestCase):
    def test_stats(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("stats-test"))
            code, out, _ = run_cli("-C", ts.dir, "stats")
            self.assertEqual(code, 0)
            self.assertIn("Profiles", out)
            self.assertIn("1", out)


class TestCLIExportImport(unittest.TestCase):
    def test_export_import_roundtrip(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("roundtrip"))
            export_path = os.path.join(ts.dir, "export.json")
            code, _, _ = run_cli("-C", ts.dir, "export", "roundtrip", "--output", export_path)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(export_path))

            # Import into a new store
            d2 = tempfile.mkdtemp()
            try:
                code2, _, _ = run_cli("-C", d2, "import", export_path)
                self.assertEqual(code2, 0)
                store2 = Store(d2)
                loaded = store2.get("roundtrip")
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded["name"], "roundtrip")
            finally:
                import shutil
                shutil.rmtree(d2, ignore_errors=True)


class TestCLIGraph(unittest.TestCase):
    def test_graph_export(self):
        with TempStore() as ts:
            ts.store.save(make_sample_profile("graph-test"))
            out_file = os.path.join(ts.dir, "graph.json")
            code, out, _ = run_cli("-C", ts.dir, "graph", "graph-test", "--output", out_file)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(out_file))
            data = json.loads(Path(out_file).read_text())
            self.assertIn("nodes", data)
            self.assertIn("edges", data)


class TestCLIVersion(unittest.TestCase):
    def test_version(self):
        code, out, _ = run_cli("--version")
        self.assertEqual(code, 0)
        self.assertIn("envforge", out)


class TestCLIHelp(unittest.TestCase):
    def test_no_command_shows_help(self):
        code, out, _ = run_cli()
        self.assertEqual(code, 0)
        self.assertIn("usage", out.lower())


if __name__ == "__main__":
    unittest.main()
