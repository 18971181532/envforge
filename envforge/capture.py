"""Environment state capture — OS, shell, tools, env vars, packages."""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _run(cmd, timeout=8):
    """Run a command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env=os.environ.copy(),
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "", "", -1


def capture_os():
    """Capture operating system information."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }


def capture_shell():
    """Detect current shell and version."""
    shell_name = "unknown"
    shell_version = "unknown"
    shell_path = os.environ.get("SHELL", "") or os.environ.get("ComSpec", "")

    if sys.platform == "win32":
        # Detect PowerShell vs CMD
        ps_module = os.environ.get("PSModulePath", "")
        if ps_module:
            shell_name = "powershell"
            out, _, rc = _run(["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"])
            if rc == 0 and out:
                shell_version = out
        else:
            shell_name = "cmd"
            out, _, rc = _run(["cmd", "/c", "ver"])
            if rc == 0 and out:
                m = re.search(r"\[Version ([^\]]+)\]", out)
                if m:
                    shell_version = m.group(1)
    else:
        if "zsh" in shell_path:
            shell_name = "zsh"
        elif "bash" in shell_path:
            shell_name = "bash"
        elif "fish" in shell_path:
            shell_name = "fish"
        else:
            shell_name = Path(shell_path).stem if shell_path else "unknown"
        out, _, rc = _run([shell_path or shell_name, "--version"])
        if rc == 0 and out:
            first_line = out.split("\n")[0]
            m = re.search(r"(\d+\.\d+(?:\.\d+)?)", first_line)
            if m:
                shell_version = m.group(1)

    return {"name": shell_name, "version": shell_version, "path": shell_path}


# Tools to detect: (name, version_cmd, version_regex)
_TOOL_SPECS = [
    ("git", ["git", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("python", [sys.executable, "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("node", ["node", "--version"], r"v?(\d+\.\d+(?:\.\d+)?)"),
    ("npm", ["npm", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("yarn", ["yarn", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("pnpm", ["pnpm", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("cargo", ["cargo", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("rustc", ["rustc", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("go", ["go", "version"], r"go(\d+\.\d+(?:\.\d+)?)"),
    ("java", ["java", "-version"], r'version "?(\d+(?:\.\d+)*)"?'),
    ("javac", ["javac", "-version"], r"(\d+(?:\.\d+)*)"),
    ("docker", ["docker", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("docker-compose", ["docker-compose", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("kubectl", ["kubectl", "version", "--client", "--short"], r"v?(\d+\.\d+(?:\.\d+)?)"),
    ("helm", ["helm", "version", "--short"], r"v?(\d+\.\d+(?:\.\d+)?)"),
    ("terraform", ["terraform", "version"], r"v?(\d+\.\d+(?:\.\d+)?)"),
    ("ansible", ["ansible", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("make", ["make", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("cmake", ["cmake", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("gcc", ["gcc", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("g++", ["g++", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("clang", ["clang", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("vim", ["vim", "--version"], r"(\d+\.\d+)"),
    ("nvim", ["nvim", "--version"], r"v?(\d+\.\d+(?:\.\d+)?)"),
    ("tmux", ["tmux", "-V"], r"(\d+\.\d+)"),
    ("curl", ["curl", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("wget", ["wget", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("ssh", ["ssh", "-V"], r"_([\d.]+p?\d*)"),
    ("rsync", ["rsync", "--version"], r"version (\d+\.\d+(?:\.\d+)?)"),
    ("jq", ["jq", "--version"], r"jq-?(\d+\.\d+(?:\.\d+)?)"),
    ("gh", ["gh", "--version"], r"gh version (\d+\.\d+(?:\.\d+)?)"),
    ("code", ["code", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("postgres", ["psql", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("mysql", ["mysql", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("redis", ["redis-cli", "--version"], r"v=(\d+\.\d+(?:\.\d+)?)"),
    ("mongo", ["mongosh", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("sqlite", ["sqlite3", "--version"], r"(\d+\.\d+(?:\.\d+)?)"),
    ("nginx", ["nginx", "-v"], r"/(\d+\.\d+(?:\.\d+)?)"),
    ("apache", ["apache2", "-v"], r"/(\d+\.\d+(?:\.\d+)?)"),
]


def capture_tools():
    """Detect installed development tools and their versions."""
    tools = {}
    for name, cmd, pattern in _TOOL_SPECS:
        path = shutil.which(cmd[0])
        if not path:
            continue
        out, err, rc = _run(cmd)
        combined = out or err
        version = "unknown"
        if combined:
            m = re.search(pattern, combined)
            if m:
                version = m.group(1)
        tools[name] = {"version": version, "path": path}
    return tools


def capture_env_vars(include_patterns=None):
    """Capture environment variables. By default captures common dev-related vars."""
    if include_patterns is None:
        include_patterns = [
            r"^PATH$", r"^HOME$", r"^USER$", r"^USERNAME$", r"^SHELL$",
            r"^LANG$", r"^LC_\w+$", r"^TERM$", r"^EDITOR$", r"^VISUAL$",
            r"^PAGER$", r"^GOPATH$", r"^GOROOT$", r"^CARGO_HOME$",
            r"^RUSTUP_HOME$", r"^NVM_DIR$", r"^NODE_PATH$", r"^PYTHONPATH$",
            r"^VIRTUAL_ENV$", r"^CONDA_\w+$", r"^JAVA_HOME$", r"^ANDROID_HOME$",
            r"^ANDROID_SDK_ROOT$", r"^DOCKER_\w+$", r"^KUBECONFIG$",
            r"^AWS_\w+$", r"^GITHUB_\w+$", r"^CI$", r"^DEBUG$",
            r"^HTTP_PROXY$", r"^HTTPS_PROXY$", r"^NO_PROXY$",
            r"^http_proxy$", r"^https_proxy$", r"^no_proxy$",
            r"^XDG_\w+$", r"^TMPDIR$", r"^TEMP$", r"^TMP$",
            r"^ComSpec$", r"^PSModulePath$", r"^PROGRAMFILES$",
            r"^PROGRAMFILES\(X86\)$", r"^LOCALAPPDATA$", r"^APPDATA$",
            r"^USERPROFILE$", r"^PUBLIC$", r"^SYSTEMROOT$",
            r"^DRIVERDATA$", r"^COMMONPROGRAMFILES$",
        ]
    compiled = [re.compile(p, re.IGNORECASE) for p in include_patterns]
    captured = {}
    for key, value in os.environ.items():
        if any(p.match(key) for p in compiled):
            captured[key] = value
    return captured


def capture_packages():
    """Capture installed packages across multiple package managers."""
    packages = {}

    # pip
    pip_path = shutil.which("pip") or shutil.which("pip3")
    if pip_path:
        out, _, rc = _run([pip_path, "list", "--format=json"], timeout=15)
        if rc == 0 and out:
            try:
                data = json.loads(out)
                packages["pip"] = [
                    {"name": p.get("name", ""), "version": p.get("version", "")}
                    for p in data
                ]
            except (json.JSONDecodeError, ValueError):
                packages["pip"] = []

    # npm global
    npm_path = shutil.which("npm")
    if npm_path:
        out, _, rc = _run([npm_path, "list", "-g", "--json", "--depth=0"], timeout=10)
        if rc == 0 and out:
            try:
                data = json.loads(out)
                deps = data.get("dependencies", {})
                packages["npm_global"] = [
                    {"name": name, "version": info.get("version", "")}
                    for name, info in deps.items()
                ]
            except (json.JSONDecodeError, ValueError):
                packages["npm_global"] = []

    # cargo
    cargo_path = shutil.which("cargo")
    if cargo_path:
        out, _, rc = _run([cargo_path, "install", "--list"], timeout=8)
        if rc == 0 and out:
            crates = []
            for line in out.split("\n"):
                line = line.strip()
                if line and not line.startswith("."):
                    m = re.match(r"^(\S+)\s+v([\d.]+)", line)
                    if m:
                        crates.append({"name": m.group(1), "version": m.group(2)})
            packages["cargo"] = crates

    # go (only if go.mod exists in cwd)
    go_path = shutil.which("go")
    if go_path and os.path.exists("go.mod"):
        out, _, rc = _run([go_path, "list", "-m", "all"], timeout=8)
        if rc == 0 and out:
            mods = []
            for line in out.split("\n"):
                parts = line.strip().split()
                if len(parts) >= 2:
                    mods.append({"name": parts[0], "version": parts[1]})
            packages["go_modules"] = mods

    return packages


def capture_git_config():
    """Capture global git configuration."""
    config = {}
    git_path = shutil.which("git")
    if not git_path:
        return config
    out, _, rc = _run([git_path, "config", "--global", "--list"])
    if rc == 0 and out:
        for line in out.split("\n"):
            if "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()
    return config


def capture_paths():
    """Capture important filesystem paths."""
    paths = {}
    home = Path.home()
    paths["home"] = str(home)
    paths["cwd"] = os.getcwd()

    # Check for common config directories
    for name, rel in [
        ("ssh", ".ssh"),
        ("gnupg", ".gnupg"),
        ("config", ".config"),
        ("vim", ".vim"),
        ("nvim", ".config/nvim"),
        ("vscode", ".vscode"),
        ("projects", "Documents/git"),
        ("projects_alt", "projects"),
        ("workspace", "workspace"),
    ]:
        p = home / rel
        if p.exists():
            paths[name] = str(p)

    return paths


def capture_shell_aliases():
    """Capture shell aliases (best effort)."""
    aliases = {}
    if sys.platform == "win32":
        return aliases
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        out, _, rc = _run(["bash", "-ic", "alias"])
        if rc == 0 and out:
            for line in out.split("\n"):
                m = re.match(r"^alias\s+(\S+)='(.+)'$", line.strip())
                if m:
                    aliases[m.group(1)] = m.group(2)
    elif "zsh" in shell:
        out, _, rc = _run(["zsh", "-ic", "alias"])
        if rc == 0 and out:
            for line in out.split("\n"):
                m = re.match(r"^(\S+)='(.+)'$", line.strip())
                if m:
                    aliases[m.group(1)] = m.group(2)
    return aliases


def capture_environment(name=None, include_packages=True):
    """Capture full environment state as a profile dict."""
    profile = {
        "name": name or f"capture_{int(time.time())}",
        "captured_at": int(time.time()),
        "captured_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "os": capture_os(),
        "shell": capture_shell(),
        "tools": capture_tools(),
        "env_vars": capture_env_vars(),
        "git_config": capture_git_config(),
        "paths": capture_paths(),
        "aliases": capture_shell_aliases(),
    }
    if include_packages:
        profile["packages"] = capture_packages()
    else:
        profile["packages"] = {}
    return profile


def summarize_profile(profile):
    """Return a brief summary of a profile."""
    tools_count = len(profile.get("tools", {}))
    pkg_count = sum(len(v) for v in profile.get("packages", {}).values())
    env_count = len(profile.get("env_vars", {}))
    return {
        "name": profile.get("name", "?"),
        "os": f"{profile.get('os', {}).get('system', '?')} {profile.get('os', {}).get('release', '')}",
        "shell": f"{profile.get('shell', {}).get('name', '?')} {profile.get('shell', {}).get('version', '')}",
        "tools": tools_count,
        "packages": pkg_count,
        "env_vars": env_count,
        "captured_at": profile.get("captured_at_iso", "?"),
    }
