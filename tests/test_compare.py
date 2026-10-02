"""Tests for envforge.compare module."""
import unittest
from tests.helpers import make_sample_profile
from envforge.compare import compare_profiles, format_compare_report


class TestCompareProfiles(unittest.TestCase):
    def test_identical_profiles(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        diff = compare_profiles(a, b)
        self.assertEqual(diff["summary"]["total_differences"], 0)

    def test_diff_structure(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        diff = compare_profiles(a, b)
        for key in ["a", "b", "a_captured", "b_captured", "summary",
                     "os", "shell", "tools", "env_vars", "packages",
                     "git_config", "paths"]:
            self.assertIn(key, diff)

    def test_tool_only_in_a(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        a["tools"]["only-a-tool"] = {"version": "1.0", "path": "/x"}
        diff = compare_profiles(a, b)
        only_a = [t for t in diff["tools"] if t["type"] == "only_in_a"]
        self.assertTrue(any(t["name"] == "only-a-tool" for t in only_a))

    def test_tool_only_in_b(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        b["tools"]["only-b-tool"] = {"version": "2.0", "path": "/y"}
        diff = compare_profiles(a, b)
        only_b = [t for t in diff["tools"] if t["type"] == "only_in_b"]
        self.assertTrue(any(t["name"] == "only-b-tool" for t in only_b))

    def test_tool_version_different(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        a["tools"]["git"]["version"] = "1.0.0"
        b["tools"]["git"]["version"] = "2.0.0"
        diff = compare_profiles(a, b)
        version_diffs = [t for t in diff["tools"] if t["type"] == "version_different"]
        self.assertTrue(any(t["name"] == "git" for t in version_diffs))

    def test_package_differences(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        a["packages"]["pip"].append({"name": "extra-pkg", "version": "1.0"})
        diff = compare_profiles(a, b)
        self.assertIn("pip", diff["packages"])
        pip_changes = diff["packages"]["pip"]
        self.assertTrue(any(c["name"] == "extra-pkg" for c in pip_changes))

    def test_os_differences(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        a["os"]["system"] = "Linux"
        b["os"]["system"] = "Darwin"
        diff = compare_profiles(a, b)
        self.assertTrue(len(diff["os"]) > 0)

    def test_profile_names_in_result(self):
        a = make_sample_profile("profile-alpha")
        b = make_sample_profile("profile-beta")
        diff = compare_profiles(a, b)
        self.assertEqual(diff["a"], "profile-alpha")
        self.assertEqual(diff["b"], "profile-beta")


class TestFormatCompareReport(unittest.TestCase):
    def test_identical_profiles_message(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        diff = compare_profiles(a, b)
        report = format_compare_report(diff)
        self.assertIn("identical", report)

    def test_report_contains_profile_names(self):
        a = make_sample_profile("alpha")
        b = make_sample_profile("beta")
        diff = compare_profiles(a, b)
        report = format_compare_report(diff)
        self.assertIn("alpha", report)
        self.assertIn("beta", report)

    def test_report_with_tool_diff(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        a["tools"]["uniquetool"] = {"version": "1.0", "path": "/x"}
        diff = compare_profiles(a, b)
        report = format_compare_report(diff)
        self.assertIn("uniquetool", report)
        self.assertIn("Tools", report)


if __name__ == "__main__":
    unittest.main()
