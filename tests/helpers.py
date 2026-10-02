"""Test helpers — temporary store and CLI runner."""
import io
import os
import sys
import tempfile
import shutil
from contextlib import contextmanager

from envforge.store import Store
from envforge.cli import main as cli_main


class TempStore:
    """Context manager that creates a temp directory with an initialized store."""

    def __init__(self):
        self.dir = tempfile.mkdtemp()
        self.store = Store(self.dir)

    def __enter__(self):
        self.store.init()
        return self

    def __exit__(self, *args):
        shutil.rmtree(self.dir, ignore_errors=True)


def run_cli(*args):
    """Run the CLI with given args, return (exit_code, stdout, stderr)."""
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = cli_main(list(args))
        return code or 0, sys.stdout.getvalue(), sys.stderr.getvalue()
    except SystemExit as e:
        return e.code or 0, sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def make_sample_profile(name="test-profile", **overrides):
    """Create a minimal sample profile dict for testing."""
    profile = {
        "name": name,
        "captured_at": 1700000000,
        "captured_at_iso": "2023-11-14T22:13:20",
        "os": {
            "system": "Linux",
            "release": "5.15.0",
            "version": "#1 SMP",
            "machine": "x86_64",
            "processor": "x86_64",
            "python_version": "3.11.4",
            "python_implementation": "CPython",
        },
        "shell": {"name": "bash", "version": "5.1.16", "path": "/bin/bash"},
        "tools": {
            "git": {"version": "2.34.1", "path": "/usr/bin/git"},
            "python": {"version": "3.11.4", "path": "/usr/bin/python3"},
            "node": {"version": "18.17.0", "path": "/usr/bin/node"},
            "npm": {"version": "9.6.7", "path": "/usr/bin/npm"},
        },
        "env_vars": {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/home/testuser",
            "USER": "testuser",
            "SHELL": "/bin/bash",
            "LANG": "en_US.UTF-8",
            "EDITOR": "vim",
            "PYTHONPATH": "/opt/python/libs",
        },
        "packages": {
            "pip": [
                {"name": "requests", "version": "2.31.0"},
                {"name": "flask", "version": "2.3.2"},
                {"name": "numpy", "version": "1.24.3"},
            ],
            "npm_global": [
                {"name": "typescript", "version": "5.2.2"},
                {"name": "eslint", "version": "8.47.0"},
            ],
        },
        "git_config": {
            "user.name": "Test User",
            "user.email": "test@example.com",
            "init.defaultBranch": "main",
        },
        "paths": {
            "home": "/home/testuser",
            "cwd": "/home/testuser/project",
            "ssh": "/home/testuser/.ssh",
        },
        "aliases": {},
    }
    profile.update(overrides)
    return profile
