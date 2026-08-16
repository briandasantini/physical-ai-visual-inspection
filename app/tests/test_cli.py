import tempfile
import unittest
from pathlib import Path

from visual_inspection.cli import build_parser, selected_pairs


class CliTests(unittest.TestCase):
    def test_parses_pair_inspection(self):
        args = build_parser().parse_args(
            ["inspect", "--pair", "r1_baseline", "--mode", "both"]
        )

        self.assertEqual(args.command, "inspect")
        self.assertEqual(args.models, ["reason2-8b"])
        self.assertEqual(args.mode, "both")

    def test_empty_data_root_has_no_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(selected_pairs(directory), [])

    def test_custom_reference_requires_live_at_runtime(self):
        args = build_parser().parse_args(
            ["inspect", "--reference", str(Path("reference.jpg"))]
        )

        self.assertIsNone(args.live)

    def test_parses_contour_controls(self):
        args = build_parser().parse_args(
            [
                "inspect",
                "--pair",
                "r1_tilt",
                "--threshold",
                "35",
                "--min-area",
                "1500",
                "--diff-method",
                "edges",
            ]
        )

        self.assertEqual(args.threshold, 35)
        self.assertEqual(args.min_area, 1500)
        self.assertEqual(args.diff_method, "edges")

    def test_parses_parameter_sweep(self):
        args = build_parser().parse_args(
            [
                "sweep",
                "--pair",
                "r1_tilt",
                "--thresholds",
                "15",
                "25",
                "--diff-methods",
                "color",
                "edges",
            ]
        )

        self.assertEqual(args.command, "sweep")
        self.assertEqual(args.thresholds, [15, 25])
        self.assertEqual(args.diff_methods, ["color", "edges"])


if __name__ == "__main__":
    unittest.main()
