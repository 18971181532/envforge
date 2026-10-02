# EnvForge

**Local-first reproducible development environment manager.**

Capture your entire development environment — OS, shell, tools, packages, environment variables, git config — as a versioned profile. Compare profiles across machines, detect drift over time, and generate bootstrap scripts to recreate an environment from scratch. Zero third-party dependencies.

---

## Features

### 🔍 Environment Capture
- **Full snapshot**: OS, shell, 40+ development tools, packages (pip/npm/cargo/go), env vars, git config, paths
- **Incremental history**: every capture is stored as a historical snapshot
- **Fast**: pure stdlib, no external dependencies

### 📊 Drift Detection
- Compare your **current environment** against any captured profile
- Categorized changes: added / removed / modified / version-changed
- Covers tools, packages, env vars, OS, shell, git config

### 🔄 Profile Comparison
- Side-by-side diff of any two profiles
- Great for "works on my machine" debugging
- Compare dev vs staging vs production environments

### 🚀 Bootstrap Generation
- Generate a shell script (bash / PowerShell / CMD) that recreates the environment
- Installs packages, configures git, sets env vars
- Perfect for onboarding new team members or setting up a new machine

### 🌐 Interactive Dashboard
- Canvas-based environment graph (OS → Shell → Tools → Package Managers → Packages)
- Profile browser with detailed tool/package listings
- Drift visualization with color-coded categories
- Profile comparison view
- Dark theme, pan/zoom graph

### 📦 Export / Import
- Export profiles as portable JSON files
- Import on another machine to share environments

---

## Installation

```bash
pip install -e .
```

Or run directly without installation:

```bash
python -m envforge --help
```

Requires Python 3.9+. No third-party dependencies.

---

## Quick Start

```bash
# 1. Initialize in your project
envforge init

# 2. Capture your environment
envforge capture dev-machine

# 3. List all profiles
envforge list

# 4. View profile details
envforge show dev-machine

# 5. Check for drift (current env vs captured profile)
envforge diff dev-machine

# 6. Compare two profiles
envforge compare dev-machine ci-machine

# 7. Generate a bootstrap script for a new machine
envforge bootstrap dev-machine --shell bash

# 8. Start the web dashboard
envforge serve --port 8765
```

---

## CLI Reference

| Command | Description |
|---|---|
| `envforge init` | Initialize EnvForge store (`.envforge/`) |
| `envforge capture [name]` | Capture current environment as a profile |
| `envforge list` | List all profiles |
| `envforge show <name>` | Show profile details |
| `envforge diff <name>` | Detect drift between current env and profile |
| `envforge compare <a> <b>` | Compare two profiles |
| `envforge bootstrap <name>` | Generate bootstrap script |
| `envforge activate <name>` | Generate activation script (env vars only) |
| `envforge delete <name>` | Delete a profile |
| `envforge history <name>` | Show capture history for a profile |
| `envforge export <name>` | Export profile to JSON |
| `envforge import <file>` | Import profile from JSON |
| `envforge stats` | Show store statistics |
| `envforge graph <name>` | Export environment graph as JSON |
| `envforge serve [--port]` | Start web dashboard |

### Options

- `-C, --directory`: Working directory (default: current)
- `capture --no-packages`: Skip package listing (faster)
- `bootstrap --shell bash|powershell|cmd|auto`: Target shell
- `serve --port 8765 --host 127.0.0.1`: Dashboard binding

---

## Web Dashboard

```bash
envforge serve
# Open http://127.0.0.1:8765
```

The dashboard provides:
- **Graph tab**: Interactive Canvas visualization of your environment hierarchy
- **Details tab**: Complete profile breakdown with tools, packages, env vars
- **Drift tab**: Color-coded drift analysis against current environment
- **Compare tab**: Side-by-side comparison of two profiles

---

## How It Works

EnvForge stores everything under `.envforge/` in your project directory:

```
.envforge/
├── meta.json              # Store metadata
├── profiles/
│   ├── dev-machine.json   # Latest profile snapshot
│   └── ci-machine.json
└── history/
    ├── dev-machine/
    │   ├── 1696000000.json  # Historical snapshots
    │   └── 1696100000.json
    └── ci-machine/
```

Each profile is a self-contained JSON document:

```json
{
  "name": "dev-machine",
  "captured_at": 1696000000,
  "os": { "system": "Windows", "release": "10", "python_version": "3.11.4" },
  "shell": { "name": "powershell", "version": "7.3.6" },
  "tools": {
    "git": { "version": "2.42.0", "path": "C:/Program Files/Git/cmd/git.exe" },
    "node": { "version": "18.17.0", "path": "C:/nodejs/node.exe" }
  },
  "packages": {
    "pip": [{ "name": "requests", "version": "2.31.0" }],
    "npm_global": [{ "name": "typescript", "version": "5.2.2" }]
  },
  "env_vars": { "PATH": "...", "PYTHONPATH": "..." },
  "git_config": { "user.name": "...", "user.email": "..." }
}
```

---

## Use Cases

- **Onboarding**: New team member runs `envforge bootstrap dev-machine` to get set up
- **"Works on my machine"**: Capture both environments and `envforge compare` to find differences
- **CI/CD parity**: Capture CI environment and compare with local dev
- **Environment audit**: Periodically capture and review what's installed
- **Machine migration**: Capture old machine, bootstrap on new machine
- **Drift monitoring**: Schedule `envforge diff` to detect unexpected environment changes

---

## Project Structure

```
envforge/
├── __init__.py          # Package metadata
├── __main__.py          # python -m envforge entry
├── capture.py           # Environment state capture (OS/shell/tools/packages/env)
├── store.py             # Profile storage (JSON files, history, import/export)
├── drift.py             # Drift detection (current env vs profile)
├── compare.py           # Profile comparison (profile vs profile)
├── bootstrap.py         # Bootstrap script generation (bash/powershell/cmd)
├── graph.py             # Environment graph construction
├── cli.py               # Command-line interface (15 subcommands)
├── server.py            # HTTP server + REST API
└── web/
    ├── index.html       # Dashboard UI
    ├── style.css        # Dark theme styles
    └── app.js           # Canvas graph + interactions
tests/
├── test_capture.py
├── test_store.py
├── test_drift.py
├── test_compare.py
├── test_bootstrap.py
├── test_graph.py
└── test_cli.py
```

---

## Testing

```bash
python -m unittest discover -s tests -v
```

---

## License

MIT
