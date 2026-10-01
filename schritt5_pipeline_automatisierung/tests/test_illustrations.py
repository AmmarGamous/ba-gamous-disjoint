"""Unit-Tests für die Algorithmusabbildungen von Schritt 5."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from xml.etree import ElementTree


STEP5_ROOT = Path(__file__).resolve().parents[1]
ILLUSTRATION_ROOT = STEP5_ROOT / "illustrations"
if str(ILLUSTRATION_ROOT) not in sys.path:
    sys.path.insert(0, str(ILLUSTRATION_ROOT))

import create_thesis_figures as figures


class ThesisIllustrationTest(unittest.TestCase):
    """Prüft Pfadauswahl und Baumgrundgerüste der Illustrationen."""

    def test_zero_max_paths_keeps_all_paths(self):
        """Prüft, dass der Standardwert 0 keine Pfade abschneidet."""
        paths = [["s", index, "d"] for index in range(5)]

        self.assertEqual(figures.first_paths(paths, 0), paths)

    def test_disjointness_graph_has_two_edps_but_only_one_ndp(self):
        """Prüft Graphgenerator, Disjunktheit, Knotenausfall und Routing."""
        graph = figures.create_disjointness_strength_graph()
        analysis = figures.analyze_disjointness_routing(graph)

        self.assertEqual(graph.graph["graph_type"], "erdos_renyi")
        self.assertEqual(graph.graph["seed"], 21)
        self.assertEqual(len(analysis["edps"]), 2)
        self.assertEqual(len(analysis["ndps"]), 1)
        self.assertTrue(all("x" in path[1:-1] for path in analysis["edps"]))
        self.assertIn("x", analysis["ndps"][0][1:-1])
        self.assertTrue(analysis["edp_before"].success)
        self.assertFalse(analysis["edp_after"].success)
        self.assertTrue(analysis["ndp_before"].success)
        self.assertFalse(analysis["ndp_after"].success)

    def test_thesis_comparison_uses_one_graph_for_all_variants(self):
        """Prüft Pfade und sichtbares Baumwachstum der Seed-430-Szene."""
        graph, metadata = figures.thesis_comparison_scene()
        edps = metadata["paths"]["edp"]
        ndps = metadata["paths"]["ndp"]

        self.assertEqual(graph.number_of_nodes(), 10)
        self.assertEqual(metadata["config"]["graph_type"], "erdos_renyi")
        self.assertEqual(metadata["config"]["p"], 0.35)
        self.assertEqual(metadata["config"]["seed"], 430)
        self.assertEqual(len(edps), 3)
        self.assertEqual(len(ndps), 2)
        self.assertNotIn(
            figures.BRANCH_COLOR,
            figures.THESIS_PATH_COLORS,
        )
        self.assertTrue(figures.shared_inner_nodes(edps))
        self.assertFalse(figures.shared_inner_nodes(ndps))

        added_edges = {}
        for path_type, paths in (("edp", edps), ("ndp", ndps)):
            one_tree = metadata["structures"][f"{path_type}_one_tree"]
            multiple_trees = metadata["structures"][
                f"{path_type}_multiple_trees"
            ]
            self.assertEqual(len(one_tree), len(paths))
            self.assertEqual(sum(item.is_tree for item in one_tree), 1)
            self.assertEqual(len(multiple_trees), len(paths))
            self.assertTrue(all(item.is_tree for item in multiple_trees))
            for structure_type, structures in (
                ("one_tree", one_tree),
                ("multiple_trees", multiple_trees),
            ):
                added_edges[f"{path_type}_{structure_type}"] = sum(
                    frozenset(edge)
                    not in {
                        frozenset(path_edge)
                        for path_edge in zip(
                            structure.original_path,
                            structure.original_path[1:],
                        )
                    }
                    for structure in structures
                    for edge in structure.graph.edges
                )

        self.assertEqual(
            added_edges,
            {
                "edp_one_tree": 2,
                "edp_multiple_trees": 5,
                "ndp_one_tree": 4,
                "ndp_multiple_trees": 5,
            },
        )

    def test_failure_comparison_uses_exactly_the_incident_edges(self):
        """Prüft gezielte Ausfälle, Reproduzierbarkeit und unveränderte Topologie."""
        graph, metadata = figures.failure_comparison_scene()
        repeated_graph, repeated_metadata = figures.failure_comparison_scene()
        node = metadata["failed_node"]

        self.assertEqual(metadata, repeated_metadata)
        self.assertEqual(set(graph.edges), set(repeated_graph.edges))
        self.assertEqual(graph.graph["seed"], 21)
        self.assertEqual(graph.number_of_edges(), 10)
        self.assertNotIn(node, (figures.SOURCE, figures.DESTINATION))
        self.assertEqual(len(metadata["link_failed_edges"]), 1)
        self.assertEqual(
            {frozenset(edge) for edge in metadata["node_failed_edges"]},
            {frozenset(edge) for edge in graph.edges(node)},
        )
        self.assertEqual(len(metadata["node_failed_edges"]), 5)
        self.assertIn(metadata["link_failed_edges"][0], metadata["node_failed_edges"])

        for key, connected in (("link_failed_edges", True), ("node_failed_edges", False)):
            remaining_graph = graph.copy()
            remaining_graph.remove_edges_from(metadata[key])
            self.assertEqual(
                figures.nx.has_path(remaining_graph, figures.SOURCE, figures.DESTINATION),
                connected,
            )

    def test_failure_comparison_scene_is_explicitly_selectable(self):
        """Der neue Vergleich ändert die bisherige Standardausgabe nicht."""
        self.assertEqual(figures.parse_args([]).scene, "comparison")
        self.assertEqual(
            figures.parse_args(["--scene", "failure_comparison"]).scene,
            "failure_comparison",
        )

    def test_failure_comparison_exports_svg_and_nonblank_png(self):
        """Prüft beide Präsentationsformate einschließlich sichtbarer Ausfälle."""
        with TemporaryDirectory() as output_dir:
            paths = figures.create_failure_comparison_files(output_dir)
            self.assertEqual([path.suffix for path in paths], [".svg", ".png"])
            svg_root = ElementTree.parse(paths[0]).getroot()
            self.assertTrue(svg_root.tag.endswith("svg"))
            pixels = figures.plt.imread(paths[1])
            self.assertGreater(pixels.shape[0], 500)
            red_pixels = (
                (pixels[:, :, 0] > 0.6)
                & (pixels[:, :, 1] < 0.35)
                & (pixels[:, :, 2] < 0.35)
            )
            self.assertGreater(red_pixels.sum(), 100)

    def test_pipeline_overview_exports_all_four_stages(self):
        """Prüft die Auswahl und beide Ausgabeformate der Ablaufgrafik."""
        self.assertEqual(figures.parse_args(["--scene", "pipeline"]).scene, "pipeline")
        with TemporaryDirectory() as output_dir:
            paths = figures.create_pipeline_overview_files(output_dir)
            self.assertEqual([path.suffix for path in paths], [".svg", ".png"])
            self.assertTrue(ElementTree.parse(paths[0]).getroot().tag.endswith("svg"))
            svg = paths[0].read_text(encoding="utf-8")
            for stage in ("Konfiguration", "Experimente", "Auswertung", "Plots"):
                self.assertIn(stage, svg)
            pixels = figures.plt.imread(paths[1])
            self.assertGreater(pixels.shape[1], 2000)
            self.assertLess(pixels[:, :, :3].min(), 0.5)

    def test_existing_base_path_exits_are_not_redrawn(self):
        """Prüft, dass nur wirklich zusätzliche Ausgänge rot gezeichnet werden."""
        structure = SimpleNamespace(exits=("a", "b", "c"))
        base_edges = {
            frozenset(("a", figures.DESTINATION)),
            frozenset(("b", figures.DESTINATION)),
        }

        self.assertEqual(
            figures._visible_additional_exits(structure, base_edges),
            [("c", figures.DESTINATION)],
        )

    def test_one_tree_uses_longest_path_and_free_edges(self):
        """Prüft die anschauliche Seed-2-Szene für EDP und NDP One Tree."""
        for path_type in ("edp", "ndp"):
            with self.subTest(path_type=path_type):
                _, _, metadata = figures.configured_scene(
                    graph_type="random_regular",
                    nodes=12,
                    degree=3,
                    seed=2,
                    algorithm=f"{path_type}_one_tree",
                    max_paths=0,
                    failure_model="none",
                )
                paths = metadata["paths"][path_type]
                structures = metadata["structures"]
                longest = max(
                    paths,
                    key=lambda path: (len(path), tuple(map(str, path))),
                )
                tree = next(
                    structure for structure in structures if structure.is_tree
                )
                other_path_edges = {
                    frozenset(edge)
                    for path in paths
                    if path != longest
                    for edge in zip(path, path[1:])
                }
                base_edges = {
                    frozenset(edge)
                    for edge in zip(longest[:-2], longest[1:-1])
                }
                added_tree_edges = {
                    frozenset(edge) for edge in tree.graph.edges
                } - base_edges

                self.assertEqual(tree.original_path, tuple(longest))
                self.assertEqual(len(structures), len(paths))
                self.assertTrue(added_tree_edges)
                self.assertTrue(added_tree_edges.isdisjoint(other_path_edges))

    def test_one_tree_label_explains_equal_length_tie_break(self):
        """Prüft die Bezeichnung eines Grundpfads bei gleicher Maximallänge."""
        paths = [["s", "a", "d"], ["s", "b", "d"]]

        first_label = figures.one_tree_path_label(
            paths[0], paths, 1, "ndp"
        )
        second_label = figures.one_tree_path_label(
            paths[1], paths, 2, "ndp"
        )

        self.assertEqual(first_label, "NDP 1")
        self.assertIn("Längengleichstand", second_label)

    def test_configured_algorithm_scene_contains_routing_result(self):
        """Prüft, dass die Abbildung die wirklich ausgeführte Route erhält."""
        _, _, metadata = figures.configured_scene(
            graph_type="random_regular",
            nodes=10,
            degree=4,
            seed=4,
            algorithm="edp_one_tree",
            failure_model="none",
        )

        self.assertTrue(metadata["routing_result"].success)
        self.assertEqual(metadata["routing_result"].route, [("s", 5), (5, "d")])


if __name__ == "__main__":
    unittest.main()
