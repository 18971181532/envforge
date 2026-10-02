"""Tests for envforge.drift module."""
import unittest
from tests.helpers import make_sample_profile
from envforge.drift import detect_drift, format_drift_report, _diff_dicts, _diff_lists


class TestDiffDicts(unittest.TestCase):
    def test_identical_dicts(self):
        a = {"x": 1, "y": 2}
        b = {"x": 1, "y": 2}
        self.assertEqual(_diff_dicts(a, b), [])

    def test_added_key(self):
        changes = _diff_dicts({"x": 1, "y": 2}, {"x": 1})
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "added")
        self.assertEqual(changes[0]["path"], "y")

    def test_removed_key(self):
        changes = _diff_dicts({"x": 1}, {"x": 1, "y": 2})
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "removed")

    def test_modified_value(self):
        changes = _diff_dicts({"x": 1}, {"x": 2})
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "modified")
        self.assertEqual(changes[0]["current"], 1)
        self.assertEqual(changes[0]["captured"], 2)

    def test_nested_dicts(self):
        a = {"outer": {"inner": 1}}
        b = {"outer": {"inner": 2}}
        changes = _diff_dicts(a, b)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["path"], "outer.inner")


class TestDiffLists(unittest.TestCase):
    def test_identical_lists(self):
        a = [{"name": "x", "version": "1.0"}]
        b = [{"name": "x", "version": "1.0"}]
        self.assertEqual(_diff_lists(a, b), [])

    def test_added_item(self):
        a = [{"name": "x", "version": "1.0"}, {"name": "y", "version": "2.0"}]
        b = [{"name": "x", "version": "1.0"}]
        changes = _diff_lists(a, b)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "added")
        self.assertEqual(changes[0]["name"], "y")

    def test_removed_item(self):
        a = [{"name": "x", "version": "1.0"}]
        b = [{"name": "x", "version": "1.0"}, {"name": "y", "version": "2.0"}]
        changes = _diff_lists(a, b)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "removed")

    def test_version_changed(self):
        a = [{"name": "x", "version": "2.0"}]
        b = [{"name": "x", "version": "1.0"}]
        changes = _diff_lists(a, b)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "version_changed")
        self.assertEqual(changes[0]["current_version"], "2.0")
        self.assertEqual(changes[0]["captured_version"], "1.0")


class TestDetectDrift(unittest.TestCase):
    def test_drift_structure(self):
        profile = make_sample_profile()
        drift = detect_drift(profile)
        for key in ["profile_name", "checked_at", "summary", "os", "shell",
                     "tools", "env_vars", "packages", "git_config", "paths"]:
            self.assertIn(key, drift)

    def test_summary_has_total_changes(self):
        profile = make_sample_profile()
        drift = detect_drift(profile)
        self.assertIn("total_changes", drift["summary"])
        self.assertGreaterEqual(drift["summary"]["total_changes"], 0)

    def test_drift_with_identical_env(self):
        """When current env matches profile exactly, no drift."""
        from envforge.capture import capture_environment
        profile = capture_environment(name="test")
        drift = detect_drift(profile, current_env=profile)
        self.assertEqual(drift["summary"]["total_changes"], 0)

    def test_drift_detects_tool_addition(self):
        profile = make_sample_profile()
        modified = make_sample_profile()
        modified["tools"]["newtool"] = {"version": "1.0", "path": "/usr/bin/newtool"}
        drift = detect_drift(profile, current_env=modified)
        tool_names = [c["name"] for c in drift["tools"] if c["type"] == "added"]
        self.assertIn("newtool", tool_names)

    def test_drift_detects_tool_removal(self):
        profile = make_sample_profile()
        modified = make_sample_profile()
        del modified["tools"]["node"]
        drift = detect_drift(profile, current_env=modified)
        tool_names = [c["name"] for c in drift["tools"] if c["type"] == "removed"]
        self.assertIn("node", tool_names)

    def test_drift_detects_version_change(self):
        profile = make_sample_profile()
        modified = make_sample_profile()
        modified["tools"]["git"]["version"] = "9.9.9"
        drift = detect_drift(profile, current_env=modified)
        version_changes = [c for c in drift["tools"] if c["type"] == "version_changed"]
        self.assertTrue(any(c["name"] == "git" for c in version_changes))


class TestFormatDriftReport(unittest.TestCase):
    def test_no_drift_message(self):
        profile = make_sample_profile()
        drift = detect_drift(profile, current_env=profile)
        report = format_drift_report(drift)
        self.assertIn("No drift detected", report)

    def test_report_contains_profile_name(self):
        profile = make_sample_profile("my-prof")
        drift = detect_drift(profile, current_env=profile)
        report = format_drift_report(drift)
        self.assertIn("my-prof", report)

    def test_report_with_changes(self):
        profile = make_sample_profile()
        modified = make_sample_profile()
        modified["tools"]["extratool"] = {"version": "1.0", "path": "/x"}
        drift = detect_drift(profile, current_env=modified)
        report = format_drift_report(drift)
        self.assertIn("extratool", report)
        self.assertIn("Tools", report)


if __name__ == "__main__":
    unittest.main()
