import tempfile
import unittest
import json
from pathlib import Path

from visual_inspection.datasets import (
    broad_category,
    discover_manifest_pairs,
    discover_workshop_pairs,
    filter_pairs,
)


class DatasetTests(unittest.TestCase):
    def test_broad_categories(self):
        self.assertEqual(broad_category("PlateRemoved"), "Remove")
        self.assertEqual(broad_category("BoxAdded"), "Add")
        self.assertEqual(broad_category("PlateShifted"), "Shift/Displace")
        self.assertEqual(broad_category("ColorSwap"), "Replace/Swap")

    def test_discovers_workshop_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "pair_0001_A_reference_ok.png"
            live = root / "pair_0001_B_test_error.png"
            reference.touch()
            live.touch()

            pairs = discover_workshop_pairs(root)

            self.assertEqual(len(pairs), 1)
            self.assertEqual(pairs[0].expected, "FAIL")

    def test_filters_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pair_0001_A_reference_ok.png").touch()
            (root / "pair_0001_B_test_error.png").touch()
            pairs = tuple(discover_workshop_pairs(root))

            self.assertEqual(len(filter_pairs(pairs, category="Curated")), 1)
            self.assertEqual(len(filter_pairs(pairs, query="pair_0001")), 1)
            self.assertEqual(len(filter_pairs(pairs, query="missing")), 0)

    def test_json_scene_does_not_fall_back_to_flat_pairing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scene = root / "Scene 01 Example"
            scene.mkdir()
            (scene / "metadata.json").write_text(json.dumps({"metadata": True}))
            (scene / "Cam_Center_G_Reference.png").touch()
            (scene / "Cam_Center_B_PlateRemoved.png").touch()

            from visual_inspection.datasets import discover_core_pairs

            self.assertEqual(discover_core_pairs(root), [])

    def test_discovers_manifest_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reference.jpg").touch()
            (root / "live.jpg").touch()
            (root / "index.json").write_text(
                json.dumps(
                    {
                        "pairs": [
                            {
                                "pair_id": "round1-test",
                                "category": "Add",
                                "expected": "FAIL",
                                "scene": "Foreign object",
                                "reference": "reference.jpg",
                                "live": "live.jpg",
                            }
                        ]
                    }
                )
            )

            pairs = discover_manifest_pairs(root, "Round 1")

            self.assertEqual(len(pairs), 1)
            self.assertEqual(pairs[0].collection, "Round 1")
            self.assertEqual(pairs[0].expected, "FAIL")


if __name__ == "__main__":
    unittest.main()
