"""Tests for envforge.capture module."""
import unittest
from envforge.capture import (
    capture_os, capture_shell, capture_tools, capture_env_vars,
    capture_packages, capture_git_config, capture_paths,
    capture_environment, summarize_profile,
)
from tests.helpers import make_sample_profile


class TestCaptureOS(unittest.TestCase):
    def test_returns_dict_with_required_keys(self):
        result = capture_os()
        self.assertIsInstance(result, dict)
        for key in ["system", "release", "version", "machine", "processor",
                     "python_version", "python_implementation"]:
            self.assertIn(key, result)

    def test_system_is_string(self):
        result = capture_os()
        self.assertIsInstance(result["system"], str)
        self.assertGreater(len(result["system"]), 0)


class TestCaptureShell(unittest.TestCase):
    def test_returns_dict(self):
        result = capture_shell()
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("version", result)
        self.assertIn("path", result)

    def test_name_is_nonempty(self):
        result = capture_shell()
        self.assertIsInstance(result["name"], str)
        self.assertGreater(len(result["name"]), 0)


class TestCaptureTools(unittest.TestCase):
    def test_returns_dict(self):
        result = capture_tools()
        self.assertIsInstance(result, dict)

    def test_python_is_detected(self):
        result = capture_tools()
        self.assertIn("python", result)
        self.assertIn("version", result["python"])
        self.assertIn("path", result["python"])

    def test_tool_values_have_version_and_path(self):
        result = capture_tools()
        for name, info in result.items():
            self.assertIn("version", info, f"{name} missing version")
            self.assertIn("path", info, f"{name} missing path")


class TestCaptureEnvVars(unittest.TestCase):
    def test_returns_dict(self):
        result = capture_env_vars()
        self.assertIsInstance(result, dict)

    def test_path_is_captured(self):
        result = capture_env_vars()
        self.assertIn("PATH", result)

    def test_custom_pattern(self):
        result = capture_env_vars(include_patterns=[r"^PATH$"])
        self.assertIn("PATH", result)
        # Should not include other vars
        for key in result:
            self.assertEqual(key, "PATH")


class TestCapturePackages(unittest.TestCase):
    def test_returns_dict(self):
        result = capture_packages()
        self.assertIsInstance(result, dict)

    def test_pip_list_structure(self):
        result = capture_packages()
        if "pip" in result:
            for pkg in result["pip"]:
                self.assertIn("name", pkg)
                self.assertIn("version", pkg)


class TestCaptureGitConfig(unittest.TestCase):
    def test_returns_dict(self):
        result = capture_git_config()
        self.assertIsInstance(result, dict)


class TestCapturePaths(unittest.TestCase):
    def test_returns_dict(self):
        result = capture_paths()
        self.assertIsInstance(result, dict)
        self.assertIn("home", result)
        self.assertIn("cwd", result)


class TestCaptureEnvironment(unittest.TestCase):
    def test_full_capture_structure(self):
        profile = capture_environment(name="test-capture", include_packages=False)
        self.assertIsInstance(profile, dict)
        for key in ["name", "captured_at", "captured_at_iso", "os", "shell",
                     "tools", "env_vars", "git_config", "paths", "aliases", "packages"]:
            self.assertIn(key, profile)

    def test_name_is_set(self):
        profile = capture_environment(name="my-env")
        self.assertEqual(profile["name"], "my-env")

    def test_no_packages_when_disabled(self):
        profile = capture_environment(include_packages=False)
        self.assertEqual(profile["packages"], {})

    def test_auto_name_when_none(self):
        profile = capture_environment()
        self.assertTrue(profile["name"].startswith("capture_"))


class TestSummarizeProfile(unittest.TestCase):
    def test_summary_keys(self):
        profile = make_sample_profile()
        summary = summarize_profile(profile)
        for key in ["name", "os", "shell", "tools", "packages", "env_vars", "captured_at"]:
            self.assertIn(key, summary)

    def test_summary_values(self):
        profile = make_sample_profile()
        summary = summarize_profile(profile)
        self.assertEqual(summary["name"], "test-profile")
        self.assertEqual(summary["tools"], 4)
        self.assertEqual(summary["packages"], 5)  # 3 pip + 2 npm
        self.assertEqual(summary["env_vars"], 7)


if __name__ == "__main__":
    unittest.main()
