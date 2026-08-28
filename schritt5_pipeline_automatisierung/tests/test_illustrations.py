"""Unit-Tests für die Algorithmusabbildungen von Schritt 5."""

from pathlib import Path
import sys
import unittest


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
