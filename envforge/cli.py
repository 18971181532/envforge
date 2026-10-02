"""EnvForge CLI — command-line interface."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import __version__
from .capture import capture_environment, summarize_profile
from .store import Store
from .drift import detect_drift, format_drift_report
from .compare import compare_profiles, format_compare_report
from .bootstrap import generate_bootstrap, generate_activation_script
from .graph import build_environment_graph, build_comparison_graph


def cmd_init(args):
    store = Store(args.directory)
    root = store.init()
    print(f"Initialized EnvForge store at {root}")
    return 0


def cmd_capture(args):
    store = Store(args.directory)
    if not store.is_initialized():
        store.init()
    name = args.name or f"capture_{int(time.time())}"
    print(f"Capturing environment as '{name}'...")
    profile = capture_environment(name=name, include_packages=not args.no_packages)
    store.save(profile)
    summary = summarize_profile(profile)
    print(f"  OS: {summary['os']}")
    print(f"  Shell: {summary['shell']}")
    print(f"  Tools: {summary['tools']}")
    print(f"  Packages: {summary['packages']}")
    print(f"  Env vars: {summary['env_vars']}")
    print(f"Saved profile '{name}'")
    return 0


def cmd_list(args):
    store = Store(args.directory)
    profiles = store.list_all()
    if not profiles:
        print("No profiles captured yet. Run 'envforge capture <name>' first.")
        return 0
    print(f"{'Name':<25} {'OS':<20} {'Shell':<18} {'Tools':>6} {'Pkgs':>6} {'Captured':<20}")
    print("-" * 100)
    for p in profiles:
        print(f"{p['name']:<25} {p['os']:<20} {p['shell']:<18} "
              f"{p['tools']:>6} {p['packages']:>6} {p['captured_at']:<20}")
    return 0


def cmd_show(args):
    store = Store(args.directory)
    profile = store.get(args.name)
    if not profile:
        print(f"Profile '{args.name}' not found", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(profile, indent=2, ensure_ascii=False))
        return 0
    summary = summarize_profile(profile)
    print(f"Profile: {summary['name']}")
    print(f"Captured: {summary['captured_at']}")
    print(f"OS: {summary['os']}")
    print(f"Shell: {summary['shell']}")
    print(f"Python: {profile.get('os', {}).get('python_version', '?')}")
    print()
    print(f"Tools ({summary['tools']}):")
    for name, info in sorted(profile.get("tools", {}).items()):
        print(f"  {name:<15} {info.get('version', '?'):<12} {info.get('path', '')}")
    print()
    packages = profile.get("packages", {})
    for mgr, pkgs in sorted(packages.items()):
        print(f"Packages ({mgr}, {len(pkgs)}):")
        for pkg in pkgs[:20]:
            print(f"  {pkg.get('name', '?'):<30} {pkg.get('version', '?')}")
        if len(pkgs) > 20:
            print(f"  ... and {len(pkgs) - 20} more")
    print()
    print(f"Environment variables ({summary['env_vars']}):")
    for key in sorted(profile.get("env_vars", {}).keys()):
        val = profile["env_vars"][key]
        display = val[:60] + "..." if len(val) > 60 else val
        print(f"  {key:<25} = {display}")
    return 0


def cmd_diff(args):
    store = Store(args.directory)
    profile = store.get(args.name)
    if not profile:
        print(f"Profile '{args.name}' not found", file=sys.stderr)
        return 1
    print(f"Detecting drift against profile '{args.name}'...")
    print()
    drift = detect_drift(profile)
    if args.json:
        print(json.dumps(drift, indent=2, ensure_ascii=False))
    else:
        print(format_drift_report(drift))
    return 0


def cmd_compare(args):
    store = Store(args.directory)
    profile_a = store.get(args.profile_a)
    profile_b = store.get(args.profile_b)
    if not profile_a:
        print(f"Profile '{args.profile_a}' not found", file=sys.stderr)
        return 1
    if not profile_b:
        print(f"Profile '{args.profile_b}' not found", file=sys.stderr)
        return 1
    diff = compare_profiles(profile_a, profile_b)
    if args.json:
        print(json.dumps(diff, indent=2, ensure_ascii=False))
    else:
        print(format_compare_report(diff))
    return 0


def cmd_bootstrap(args):
    store = Store(args.directory)
    profile = store.get(args.name)
    if not profile:
        print(f"Profile '{args.name}' not found", file=sys.stderr)
        return 1
    shell = args.shell or "auto"
    output = args.output
    if not output:
        ext = {"bash": ".sh", "powershell": ".ps1", "cmd": ".bat"}.get(shell, ".sh")
        output = f"bootstrap_{args.name}{ext}"
    script = generate_bootstrap(profile, output_path=output, shell=shell)
    print(f"Generated bootstrap script: {output}")
    print(f"  Profile: {args.name}")
    print(f"  Shell: {shell}")
    print(f"  Size: {len(script)} bytes")
    return 0


def cmd_activate(args):
    store = Store(args.directory)
    profile = store.get(args.name)
    if not profile:
        print(f"Profile '{args.name}' not found", file=sys.stderr)
        return 1
    shell = args.shell or "auto"
    script = generate_activation_script(profile, shell=shell)
    if args.output:
        Path(args.output).write_text(script, encoding="utf-8")
        print(f"Activation script written to: {args.output}")
    else:
        print(script)
    return 0


def cmd_delete(args):
    store = Store(args.directory)
    if store.delete(args.name):
        print(f"Deleted profile '{args.name}'")
    else:
        print(f"Profile '{args.name}' not found", file=sys.stderr)
        return 1
    return 0


def cmd_history(args):
    store = Store(args.directory)
    snapshots = store.history(args.name)
    if not snapshots:
        print(f"No history for profile '{args.name}'")
        return 0
    print(f"History for '{args.name}' ({len(snapshots)} snapshots):")
    for s in snapshots:
        print(f"  {s['iso']:<20} tools={s['tools']:<4} packages={s['packages']}")
    return 0


def cmd_export(args):
    store = Store(args.directory)
    output = args.output or f"{args.name}.json"
    if store.export_profile(args.name, output):
        print(f"Exported profile '{args.name}' to {output}")
    else:
        print(f"Profile '{args.name}' not found", file=sys.stderr)
        return 1
    return 0


def cmd_import(args):
    store = Store(args.directory)
    if not store.is_initialized():
        store.init()
    try:
        profile = store.import_profile(args.file)
        print(f"Imported profile '{profile['name']}'")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Import failed: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_stats(args):
    store = Store(args.directory)
    stats = store.stats()
    print(f"EnvForge Store Statistics")
    print(f"  Profiles: {stats['profiles']}")
    print(f"  History snapshots: {stats['history_snapshots']}")
    if stats["profile_names"]:
        print(f"  Profiles: {', '.join(stats['profile_names'])}")
    return 0


def cmd_graph(args):
    store = Store(args.directory)
    profile = store.get(args.name)
    if not profile:
        print(f"Profile '{args.name}' not found", file=sys.stderr)
        return 1
    graph = build_environment_graph(profile)
    output = args.output or f"graph_{args.name}.json"
    Path(output).write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"Environment graph: {output}")
    print(f"  Nodes: {graph['stats']['total_nodes']}")
    print(f"  Edges: {graph['stats']['total_edges']}")
    print(f"  Tools: {graph['stats']['tools']}")
    print(f"  Packages: {graph['stats']['packages']}")
    return 0


def cmd_serve(args):
    from .server import start_server
    start_server(args.directory, args.port, args.host)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="envforge",
        description="EnvForge — local-first reproducible development environment manager",
    )
    parser.add_argument("--version", action="version", version=f"envforge {__version__}")
    parser.add_argument("-C", "--directory", default=os.getcwd(),
                        help="Working directory (default: current)")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = sub.add_parser("init", help="Initialize EnvForge store")
    p_init.set_defaults(func=cmd_init)

    # capture
    p_cap = sub.add_parser("capture", help="Capture current environment as a profile")
    p_cap.add_argument("name", nargs="?", help="Profile name")
    p_cap.add_argument("--no-packages", action="store_true", help="Skip package listing")
    p_cap.set_defaults(func=cmd_capture)

    # list
    p_list = sub.add_parser("list", help="List all profiles")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = sub.add_parser("show", help="Show profile details")
    p_show.add_argument("name", help="Profile name")
    p_show.add_argument("--json", action="store_true", help="Output as JSON")
    p_show.set_defaults(func=cmd_show)

    # diff (drift)
    p_diff = sub.add_parser("diff", help="Detect drift between current env and a profile")
    p_diff.add_argument("name", help="Profile name to compare against")
    p_diff.add_argument("--json", action="store_true", help="Output as JSON")
    p_diff.set_defaults(func=cmd_diff)

    # compare
    p_cmp = sub.add_parser("compare", help="Compare two profiles")
    p_cmp.add_argument("profile_a", help="First profile name")
    p_cmp.add_argument("profile_b", help="Second profile name")
    p_cmp.add_argument("--json", action="store_true", help="Output as JSON")
    p_cmp.set_defaults(func=cmd_compare)

    # bootstrap
    p_boot = sub.add_parser("bootstrap", help="Generate bootstrap script for new machine")
    p_boot.add_argument("name", help="Profile name")
    p_boot.add_argument("--shell", choices=["bash", "powershell", "cmd", "auto"],
                        default="auto", help="Target shell")
    p_boot.add_argument("--output", "-o", help="Output file path")
    p_boot.set_defaults(func=cmd_bootstrap)

    # activate
    p_act = sub.add_parser("activate", help="Generate activation script for current session")
    p_act.add_argument("name", help="Profile name")
    p_act.add_argument("--shell", choices=["bash", "powershell", "auto"], default="auto")
    p_act.add_argument("--output", "-o", help="Output file path")
    p_act.set_defaults(func=cmd_activate)

    # delete
    p_del = sub.add_parser("delete", help="Delete a profile")
    p_del.add_argument("name", help="Profile name")
    p_del.set_defaults(func=cmd_delete)

    # history
    p_hist = sub.add_parser("history", help="Show capture history for a profile")
    p_hist.add_argument("name", help="Profile name")
    p_hist.set_defaults(func=cmd_history)

    # export
    p_exp = sub.add_parser("export", help="Export a profile to JSON file")
    p_exp.add_argument("name", help="Profile name")
    p_exp.add_argument("--output", "-o", help="Output file path")
    p_exp.set_defaults(func=cmd_export)

    # import
    p_imp = sub.add_parser("import", help="Import a profile from JSON file")
    p_imp.add_argument("file", help="JSON file path")
    p_imp.set_defaults(func=cmd_import)

    # stats
    p_stats = sub.add_parser("stats", help="Show store statistics")
    p_stats.set_defaults(func=cmd_stats)

    # graph
    p_graph = sub.add_parser("graph", help="Export environment graph as JSON")
    p_graph.add_argument("name", help="Profile name")
    p_graph.add_argument("--output", "-o", help="Output file path")
    p_graph.set_defaults(func=cmd_graph)

    # serve
    p_serve = sub.add_parser("serve", help="Start web dashboard")
    p_serve.add_argument("--port", "-p", type=int, default=8765, help="Port (default: 8765)")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
