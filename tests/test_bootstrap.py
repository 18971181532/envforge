"""Tests for envforge.bootstrap module."""
import os
import tempfile
import unittest
from pathlib import Path
from tests.helpers import make_sample_profile
from envforge.bootstrap import generate_bootstrap, generate_activation_script


class TestGenerateBootstrap(unittest.TestCase):
    def test_returns_string(self):
        profile = make_sample_profile()
        script = generate_bootstrap(profile, shell="bash")
        self.assertIsInstance(script, str)
        self.assertGreater(len(script), 0)

    def test_bash_shebang(self):
        profile = make_sample_profile()
        script = generate_bootstrap(profile, shell="bash")
        self.assertTrue(script.startswith("#!/usr/bin/env bash"))

    def test_powershell_header(self):
        profile = make_sample_profile()
        script = generate_bootstrap(profile, shell="powershell")
        self.assertIn("EnvForge Bootstrap", script)
        self.assertIn("powershell", script.lower())

    def test_cmd_header(self):
        profile = make_sample_profile()
        script = generate_bootstrap(profile, shell="cmd")
        self.assertTrue(script.startswith("@echo off"))

    def test_contains_pip_packages(self):
        profile = make_sample_profile()
        script = generate_bootstrap(profile, shell="bash")
        self.assertIn("requests", script)
        self.assertIn("flask", script)
        self.assertIn("numpy", script)

    def test_contains_npm_packages(self):
        profile = make_sample_profile()
        script = generate_bootstrap(profile, shell="bash")
        self.assertIn("typescript", script)
        self.assertIn("eslint", script)

    def test_contains_git_config(self):
        profile = make_sample_profile()
        script = generate_bootstrap(profile, shell="bash")
        self.assertIn("Test User", script)
        self.assertIn("test@example.com", script)

    def test_writes_to_file(self):
        profile = make_sample_profile()
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "bootstrap.sh")
            generate_bootstrap(profile, output_path=out, shell="bash")
            self.assertTrue(os.path.exists(out))
            content = Path(out).read_text()
            self.assertIn("#!/usr/bin/env bash", content)

    def test_profile_name_in_script(self):
        profile = make_sample_profile("my-special-env")
        script = generate_bootstrap(profile, shell="bash")
        self.assertIn("my-special-env", script)

    def test_empty_packages(self):
        profile = make_sample_profile()
        profile["packages"] = {}
        script = generate_bootstrap(profile, shell="bash")
        self.assertIsInstance(script, str)
        self.assertGreater(len(script), 0)

    def test_auto_shell_detection(self):
        profile = make_sample_profile()
        script = generate_bootstrap(profile, shell="auto")
        self.assertIsInstance(script, str)
        # Should produce either bash or powershell based on OS
        self.assertTrue(script.startswith("#!") or "powershell" in script.lower())

    def test_invalid_shell_raises(self):
        profile = make_sample_profile()
        with self.assertRaises(ValueError):
            generate_bootstrap(profile, shell="invalid_shell")


class TestGenerateActivationScript(unittest.TestCase):
    def test_returns_string(self):
        profile = make_sample_profile()
        script = generate_activation_script(profile, shell="bash")
        self.assertIsInstance(script, str)
        self.assertGreater(len(script), 0)

    def test_bash_activation_has_exports(self):
        profile = make_sample_profile()
        script = generate_activation_script(profile, shell="bash")
        self.assertIn("export", script)
        self.assertIn("LANG", script)
        self.assertIn("EDITOR", script)

    def test_powershell_activation_has_env(self):
        profile = make_sample_profile()
        script = generate_activation_script(profile, shell="powershell")
        self.assertIn("$env:", script)

    def test_does_not_override_path(self):
        profile = make_sample_profile()
        script = generate_activation_script(profile, shell="bash")
        # PATH should not be set as a simple export
        self.assertNotIn("export PATH=", script)

    def test_profile_name_in_activation(self):
        profile = make_sample_profile("activate-me")
        script = generate_activation_script(profile, shell="bash")
        self.assertIn("activate-me", script)


if __name__ == "__main__":
    unittest.main()
