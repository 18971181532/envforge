"""Tests for envforge.graph module."""
import unittest
from tests.helpers import make_sample_profile
from envforge.graph import build_environment_graph, build_comparison_graph


class TestBuildEnvironmentGraph(unittest.TestCase):
    def test_returns_dict_with_nodes_and_edges(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        self.assertIn("stats", graph)

    def test_has_os_node(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        os_nodes = [n for n in graph["nodes"] if n["type"] == "os"]
        self.assertEqual(len(os_nodes), 1)

    def test_has_shell_node(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        shell_nodes = [n for n in graph["nodes"] if n["type"] == "shell"]
        self.assertEqual(len(shell_nodes), 1)

    def test_has_tool_nodes(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        tool_nodes = [n for n in graph["nodes"] if n["type"] == "tool"]
        self.assertEqual(len(tool_nodes), 4)  # git, python, node, npm

    def test_has_package_nodes(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        pkg_nodes = [n for n in graph["nodes"] if n["type"] == "package"]
        # 3 pip + 2 npm = 5
        self.assertEqual(len(pkg_nodes), 5)

    def test_has_manager_nodes(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        mgr_nodes = [n for n in graph["nodes"] if n["type"] == "manager"]
        self.assertEqual(len(mgr_nodes), 2)  # pip, npm_global

    def test_edges_exist(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        self.assertGreater(len(graph["edges"]), 0)

    def test_stats(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        s = graph["stats"]
        self.assertEqual(s["tools"], 4)
        self.assertEqual(s["packages"], 5)
        self.assertEqual(s["managers"], 2)
        self.assertEqual(s["total_nodes"], len(graph["nodes"]))
        self.assertEqual(s["total_edges"], len(graph["edges"]))

    def test_node_ids_are_unique(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        ids = [n["id"] for n in graph["nodes"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_edges_reference_existing_nodes(self):
        profile = make_sample_profile()
        graph = build_environment_graph(profile)
        node_ids = {n["id"] for n in graph["nodes"]}
        for edge in graph["edges"]:
            self.assertIn(edge["source"], node_ids)
            self.assertIn(edge["target"], node_ids)

    def test_empty_profile(self):
        profile = make_sample_profile()
        profile["tools"] = {}
        profile["packages"] = {}
        graph = build_environment_graph(profile)
        # Should still have os and shell nodes
        self.assertEqual(len([n for n in graph["nodes"] if n["type"] == "os"]), 1)
        self.assertEqual(len([n for n in graph["nodes"] if n["type"] == "shell"]), 1)


class TestBuildComparisonGraph(unittest.TestCase):
    def test_identical_profiles_all_common(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        graph = build_comparison_graph(a, b)
        self.assertEqual(graph["stats"]["common"], len(graph["nodes"]))
        self.assertEqual(graph["stats"]["only_a"], 0)
        self.assertEqual(graph["stats"]["only_b"], 0)

    def test_node_only_in_a(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        a["tools"]["unique-a"] = {"version": "1.0", "path": "/x"}
        graph = build_comparison_graph(a, b)
        self.assertGreater(graph["stats"]["only_a"], 0)
        only_a_nodes = [n for n in graph["nodes"] if n.get("status") == "only_a"]
        self.assertTrue(any("unique-a" in n["id"] for n in only_a_nodes))

    def test_node_only_in_b(self):
        a = make_sample_profile("a")
        b = make_sample_profile("b")
        b["tools"]["unique-b"] = {"version": "2.0", "path": "/y"}
        graph = build_comparison_graph(a, b)
        self.assertGreater(graph["stats"]["only_b"], 0)

    def test_profile_names_in_result(self):
        a = make_sample_profile("alpha")
        b = make_sample_profile("beta")
        graph = build_comparison_graph(a, b)
        self.assertEqual(graph["profile_a"], "alpha")
        self.assertEqual(graph["profile_b"], "beta")


if __name__ == "__main__":
    unittest.main()
