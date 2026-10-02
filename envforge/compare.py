"""Profile comparison — diff two captured environments."""
from .drift import _diff_dicts, _diff_lists


def compare_profiles(profile_a, profile_b):
    """Compare two profiles and return structured differences."""
    result = {
        "a": profile_a.get("name", "A"),
        "b": profile_b.get("name", "B"),
        "a_captured": profile_a.get("captured_at_iso", ""),
        "b_captured": profile_b.get("captured_at_iso", ""),
        "summary": {
            "total_differences": 0,
            "only_in_a": 0,
            "only_in_b": 0,
            "different": 0,
        },
        "os": [],
        "shell": [],
        "tools": [],
        "env_vars": [],
        "packages": {},
        "git_config": [],
        "paths": [],
    }

    # OS
    result["os"] = _diff_dicts(
        profile_a.get("os", {}), profile_b.get("os", {}), "os"
    )
    result["summary"]["total_differences"] += len(result["os"])

    # Shell
    result["shell"] = _diff_dicts(
        profile_a.get("shell", {}), profile_b.get("shell", {}), "shell"
    )
    result["summary"]["total_differences"] += len(result["shell"])

    # Tools
    tools_a = profile_a.get("tools", {})
    tools_b = profile_b.get("tools", {})
    tool_diffs = []
    all_tools = set(tools_a.keys()) | set(tools_b.keys())
    for tool in sorted(all_tools):
        if tool in tools_a and tool not in tools_b:
            tool_diffs.append({
                "type": "only_in_a", "name": tool,
                "version_a": tools_a[tool].get("version", "?"),
            })
        elif tool in tools_b and tool not in tools_a:
            tool_diffs.append({
                "type": "only_in_b", "name": tool,
                "version_b": tools_b[tool].get("version", "?"),
            })
        elif tools_a[tool].get("version") != tools_b[tool].get("version"):
            tool_diffs.append({
                "type": "version_different", "name": tool,
                "version_a": tools_a[tool].get("version", "?"),
                "version_b": tools_b[tool].get("version", "?"),
            })
    result["tools"] = tool_diffs
    result["summary"]["total_differences"] += len(tool_diffs)
    for d in tool_diffs:
        result["summary"][d["type"]] = result["summary"].get(d["type"], 0) + 1

    # Env vars
    result["env_vars"] = _diff_dicts(
        profile_a.get("env_vars", {}), profile_b.get("env_vars", {}), "env"
    )
    result["summary"]["total_differences"] += len(result["env_vars"])

    # Packages
    pkg_a = profile_a.get("packages", {})
    pkg_b = profile_b.get("packages", {})
    all_mgrs = set(pkg_a.keys()) | set(pkg_b.keys())
    for mgr in sorted(all_mgrs):
        diffs = _diff_lists(pkg_a.get(mgr, []), pkg_b.get(mgr, []))
        result["packages"][mgr] = diffs
        result["summary"]["total_differences"] += len(diffs)

    # Git config
    result["git_config"] = _diff_dicts(
        profile_a.get("git_config", {}), profile_b.get("git_config", {}), "git"
    )
    result["summary"]["total_differences"] += len(result["git_config"])

    # Paths
    result["paths"] = _diff_dicts(
        profile_a.get("paths", {}), profile_b.get("paths", {}), "paths"
    )
    result["summary"]["total_differences"] += len(result["paths"])

    return result


def format_compare_report(diff):
    """Format comparison results as human-readable text."""
    lines = []
    s = diff["summary"]
    lines.append(f"Comparison: {diff['a']} vs {diff['b']}")
    lines.append(f"  {diff['a']} captured: {diff['a_captured']}")
    lines.append(f"  {diff['b']} captured: {diff['b_captured']}")
    lines.append(f"Total differences: {s['total_differences']}")
    lines.append("")

    # Tools
    if diff["tools"]:
        lines.append("=== Tools ===")
        for d in diff["tools"]:
            if d["type"] == "only_in_a":
                lines.append(f"  only in {diff['a']}: {d['name']} {d['version_a']}")
            elif d["type"] == "only_in_b":
                lines.append(f"  only in {diff['b']}: {d['name']} {d['version_b']}")
            elif d["type"] == "version_different":
                lines.append(f"  {d['name']}: {d['version_a']} ({diff['a']}) vs {d['version_b']} ({diff['b']})")
        lines.append("")

    # Packages
    for mgr, changes in diff["packages"].items():
        if changes:
            lines.append(f"=== Packages ({mgr}) ===")
            for c in changes:
                if c["type"] == "added":
                    lines.append(f"  only in {diff['a']}: {c['name']}")
                elif c["type"] == "removed":
                    lines.append(f"  only in {diff['b']}: {c['name']}")
                elif c["type"] == "version_changed":
                    lines.append(f"  {c['name']}: {c['captured_version']} vs {c['current_version']}")
            lines.append("")

    # Env vars
    if diff["env_vars"]:
        lines.append("=== Environment Variables ===")
        for c in diff["env_vars"]:
            path = c["path"].replace("env.", "")
            lines.append(f"  {c['type']}: {path}")
        lines.append("")

    # OS / Shell / Git / Paths
    for category in ["os", "shell", "git_config", "paths"]:
        changes = diff.get(category, [])
        if changes:
            lines.append(f"=== {category.replace('_', ' ').upper()} ===")
            for c in changes:
                lines.append(f"  {c['type']}: {c['path']}")
            lines.append("")

    if s["total_differences"] == 0:
        lines.append("Profiles are identical.")

    return "\n".join(lines)
