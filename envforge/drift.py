"""Drift detection — compare current environment against a captured profile."""
import json
import os
from .capture import capture_environment


def _diff_dicts(current, captured, path=""):
    """Recursively diff two dicts. Returns list of changes."""
    changes = []
    all_keys = set(current.keys()) | set(captured.keys())
    for key in sorted(all_keys):
        cur_path = f"{path}.{key}" if path else key
        in_cur = key in current
        in_cap = key in captured
        if in_cur and not in_cap:
            changes.append({"type": "added", "path": cur_path, "current": current[key]})
        elif in_cap and not in_cur:
            changes.append({"type": "removed", "path": cur_path, "captured": captured[key]})
        elif isinstance(current[key], dict) and isinstance(captured[key], dict):
            changes.extend(_diff_dicts(current[key], captured[key], cur_path))
        elif current[key] != captured[key]:
            changes.append({
                "type": "modified",
                "path": cur_path,
                "current": current[key],
                "captured": captured[key],
            })
    return changes


def _diff_lists(current, captured, key_field="name"):
    """Diff two lists of dicts by a key field."""
    cur_map = {item.get(key_field, ""): item for item in current}
    cap_map = {item.get(key_field, ""): item for item in captured}
    changes = []
    all_keys = set(cur_map.keys()) | set(cap_map.keys())
    for key in sorted(all_keys):
        if key in cur_map and key not in cap_map:
            changes.append({"type": "added", "name": key, "current": cur_map[key]})
        elif key in cap_map and key not in cur_map:
            changes.append({"type": "removed", "name": key, "captured": cap_map[key]})
        elif cur_map[key].get("version") != cap_map[key].get("version"):
            changes.append({
                "type": "version_changed",
                "name": key,
                "current_version": cur_map[key].get("version"),
                "captured_version": cap_map[key].get("version"),
            })
    return changes


def detect_drift(profile, current_env=None):
    """Detect drift between current environment and a captured profile.

    Returns a dict with categorized drift findings.
    """
    if current_env is None:
        current_env = capture_environment(name="__current__", include_packages=True)

    drift = {
        "profile_name": profile.get("name", "?"),
        "checked_at": current_env.get("captured_at_iso", ""),
        "summary": {
            "total_changes": 0,
            "added": 0,
            "removed": 0,
            "modified": 0,
            "version_changes": 0,
        },
        "os": {},
        "shell": {},
        "tools": [],
        "env_vars": [],
        "packages": {},
        "git_config": [],
        "paths": [],
    }

    # OS drift
    os_cur = current_env.get("os", {})
    os_cap = profile.get("os", {})
    os_changes = _diff_dicts(os_cur, os_cap, "os")
    drift["os"] = os_changes
    drift["summary"]["total_changes"] += len(os_changes)

    # Shell drift
    sh_cur = current_env.get("shell", {})
    sh_cap = profile.get("shell", {})
    sh_changes = _diff_dicts(sh_cur, sh_cap, "shell")
    drift["shell"] = sh_changes
    drift["summary"]["total_changes"] += len(sh_changes)

    # Tools drift
    tools_cur = current_env.get("tools", {})
    tools_cap = profile.get("tools", {})
    tool_changes = []
    all_tools = set(tools_cur.keys()) | set(tools_cap.keys())
    for tool in sorted(all_tools):
        if tool in tools_cur and tool not in tools_cap:
            tool_changes.append({
                "type": "added", "name": tool,
                "version": tools_cur[tool].get("version", "?"),
            })
        elif tool in tools_cap and tool not in tools_cur:
            tool_changes.append({
                "type": "removed", "name": tool,
                "version": tools_cap[tool].get("version", "?"),
            })
        elif tools_cur[tool].get("version") != tools_cap[tool].get("version"):
            tool_changes.append({
                "type": "version_changed", "name": tool,
                "current_version": tools_cur[tool].get("version", "?"),
                "captured_version": tools_cap[tool].get("version", "?"),
            })
    drift["tools"] = tool_changes
    drift["summary"]["total_changes"] += len(tool_changes)
    for c in tool_changes:
        drift["summary"][c["type"]] = drift["summary"].get(c["type"], 0) + 1

    # Env vars drift
    env_cur = current_env.get("env_vars", {})
    env_cap = profile.get("env_vars", {})
    env_changes = _diff_dicts(env_cur, env_cap, "env")
    drift["env_vars"] = env_changes
    drift["summary"]["total_changes"] += len(env_changes)
    for c in env_changes:
        drift["summary"][c["type"]] = drift["summary"].get(c["type"], 0) + 1

    # Packages drift
    pkg_cur = current_env.get("packages", {})
    pkg_cap = profile.get("packages", {})
    all_managers = set(pkg_cur.keys()) | set(pkg_cap.keys())
    for mgr in sorted(all_managers):
        cur_pkgs = pkg_cur.get(mgr, [])
        cap_pkgs = pkg_cap.get(mgr, [])
        pkg_changes = _diff_lists(cur_pkgs, cap_pkgs)
        drift["packages"][mgr] = pkg_changes
        drift["summary"]["total_changes"] += len(pkg_changes)
        for c in pkg_changes:
            drift["summary"][c["type"]] = drift["summary"].get(c["type"], 0) + 1

    # Git config drift
    git_cur = current_env.get("git_config", {})
    git_cap = profile.get("git_config", {})
    git_changes = _diff_dicts(git_cur, git_cap, "git")
    drift["git_config"] = git_changes
    drift["summary"]["total_changes"] += len(git_changes)

    # Paths drift
    paths_cur = current_env.get("paths", {})
    paths_cap = profile.get("paths", {})
    path_changes = _diff_dicts(paths_cur, paths_cap, "paths")
    drift["paths"] = path_changes
    drift["summary"]["total_changes"] += len(path_changes)

    return drift


def format_drift_report(drift):
    """Format drift results as a human-readable text report."""
    lines = []
    s = drift["summary"]
    lines.append(f"Drift report for profile '{drift['profile_name']}'")
    lines.append(f"Checked at: {drift['checked_at']}")
    lines.append(f"Total changes: {s['total_changes']} "
                 f"(+{s.get('added',0)} added, -{s.get('removed',0)} removed, "
                 f"~{s.get('modified',0)} modified, {s.get('version_changed',0)} version changes)")
    lines.append("")

    # Tools
    if drift["tools"]:
        lines.append("=== Tools ===")
        for c in drift["tools"]:
            if c["type"] == "added":
                lines.append(f"  + {c['name']} {c['version']} (new)")
            elif c["type"] == "removed":
                lines.append(f"  - {c['name']} {c['version']} (was installed)")
            elif c["type"] == "version_changed":
                lines.append(f"  ~ {c['name']}: {c['captured_version']} -> {c['current_version']}")
        lines.append("")

    # Packages
    for mgr, changes in drift["packages"].items():
        if changes:
            lines.append(f"=== Packages ({mgr}) ===")
            for c in changes:
                if c["type"] == "added":
                    lines.append(f"  + {c['name']} {c['current'].get('version','?')}")
                elif c["type"] == "removed":
                    lines.append(f"  - {c['name']} {c['captured'].get('version','?')}")
                elif c["type"] == "version_changed":
                    lines.append(f"  ~ {c['name']}: {c['captured_version']} -> {c['current_version']}")
            lines.append("")

    # Env vars
    if drift["env_vars"]:
        lines.append("=== Environment Variables ===")
        for c in drift["env_vars"]:
            path = c["path"].replace("env.", "")
            if c["type"] == "added":
                val = str(c["current"])[:80]
                lines.append(f"  + {path} = {val}")
            elif c["type"] == "removed":
                val = str(c["captured"])[:80]
                lines.append(f"  - {path} = {val}")
            elif c["type"] == "modified":
                lines.append(f"  ~ {path} changed")
        lines.append("")

    # OS / Shell
    for category in ["os", "shell"]:
        changes = drift.get(category, [])
        if changes:
            lines.append(f"=== {category.upper()} ===")
            for c in changes:
                lines.append(f"  {c['type']}: {c['path']}")
            lines.append("")

    if s["total_changes"] == 0:
        lines.append("No drift detected — environment matches profile.")

    return "\n".join(lines)
