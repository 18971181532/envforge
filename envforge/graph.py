"""Environment graph — build a visualizable graph of tools, packages, and their relationships."""


def build_environment_graph(profile):
    """Build a graph structure from a profile for visualization.

    Nodes:
    - os node (root)
    - shell node
    - tool nodes (one per detected tool)
    - package manager nodes
    - package nodes (grouped under managers)

    Edges:
    - os -> shell
    - os -> tools
    - tools -> package managers
    - package managers -> packages
    """
    nodes = []
    edges = []
    node_ids = set()

    def add_node(node_id, label, ntype, **kwargs):
        if node_id not in node_ids:
            node = {"id": node_id, "label": label, "type": ntype}
            node.update(kwargs)
            nodes.append(node)
            node_ids.add(node_id)

    def add_edge(source, target, etype="depends"):
        edges.append({"source": source, "target": target, "type": etype})

    # OS root
    os_info = profile.get("os", {})
    os_label = f"{os_info.get('system', '?')} {os_info.get('release', '')}".strip()
    add_node("os", os_label, "os", version=os_info.get("version", ""))

    # Shell
    shell_info = profile.get("shell", {})
    shell_label = f"{shell_info.get('name', '?')} {shell_info.get('version', '')}".strip()
    add_node("shell", shell_label, "shell")
    add_edge("os", "shell", "runs")

    # Tools
    tools = profile.get("tools", {})
    for tool_name, tool_info in sorted(tools.items()):
        tid = f"tool:{tool_name}"
        version = tool_info.get("version", "?")
        add_node(tid, f"{tool_name} {version}", "tool",
                 version=version, path=tool_info.get("path", ""))
        add_edge("os", tid, "installed")

        # Connect tools that are package managers to their packages
        if tool_name in ("pip", "npm", "yarn", "pnpm", "cargo", "go"):
            pass  # handled below

    # Packages
    packages = profile.get("packages", {})
    for mgr_name, pkg_list in sorted(packages.items()):
        mgr_id = f"mgr:{mgr_name}"
        add_node(mgr_id, mgr_name, "manager", count=len(pkg_list))

        # Connect manager to corresponding tool if exists
        tool_map = {
            "pip": "pip", "pip3": "pip",
            "npm_global": "npm",
            "cargo": "cargo",
            "go_modules": "go",
        }
        corresponding_tool = tool_map.get(mgr_name)
        if corresponding_tool and f"tool:{corresponding_tool}" in node_ids:
            add_edge(f"tool:{corresponding_tool}", mgr_id, "manages")
        else:
            add_edge("os", mgr_id, "installed")

        # Add package nodes (limit to avoid huge graphs)
        for pkg in pkg_list[:50]:  # Cap at 50 per manager for readability
            pkg_id = f"pkg:{mgr_name}:{pkg.get('name', '')}"
            add_node(pkg_id, f"{pkg.get('name', '?')} {pkg.get('version', '')}",
                     "package", version=pkg.get("version", ""), manager=mgr_name)
            add_edge(mgr_id, pkg_id, "contains")

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "tools": len(tools),
            "packages": sum(len(v) for v in packages.values()),
            "managers": len(packages),
        },
    }


def build_comparison_graph(profile_a, profile_b):
    """Build a graph highlighting differences between two profiles."""
    graph_a = build_environment_graph(profile_a)
    graph_b = build_environment_graph(profile_b)

    # Mark nodes by which profile they appear in
    a_ids = {n["id"] for n in graph_a["nodes"]}
    b_ids = {n["id"] for n in graph_b["nodes"]}

    all_nodes = {}
    for n in graph_a["nodes"]:
        n2 = dict(n)
        n2["in_a"] = True
        n2["in_b"] = n["id"] in b_ids
        all_nodes[n["id"]] = n2
    for n in graph_b["nodes"]:
        if n["id"] not in all_nodes:
            n2 = dict(n)
            n2["in_a"] = False
            n2["in_b"] = True
            all_nodes[n["id"]] = n2

    # Color-code
    for nid, node in all_nodes.items():
        if node["in_a"] and node["in_b"]:
            node["status"] = "common"
        elif node["in_a"]:
            node["status"] = "only_a"
        else:
            node["status"] = "only_b"

    all_edges = []
    seen_edges = set()
    for e in graph_a["edges"] + graph_b["edges"]:
        key = (e["source"], e["target"])
        if key not in seen_edges:
            all_edges.append(e)
            seen_edges.add(key)

    return {
        "nodes": list(all_nodes.values()),
        "edges": all_edges,
        "profile_a": profile_a.get("name", "A"),
        "profile_b": profile_b.get("name", "B"),
        "stats": {
            "common": sum(1 for n in all_nodes.values() if n["status"] == "common"),
            "only_a": sum(1 for n in all_nodes.values() if n["status"] == "only_a"),
            "only_b": sum(1 for n in all_nodes.values() if n["status"] == "only_b"),
        },
    }
