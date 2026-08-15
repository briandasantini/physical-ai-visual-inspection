import unittest

from PIL import Image

from visual_inspection.config import MODELS
from visual_inspection.nim_client import parse_response
from visual_inspection.vision import ContourResult


class ResponseParsingTests(unittest.TestCase):
    def test_parses_expected_response(self):
        contour = ContourResult(
            image=Image.new("RGB", (10, 10)),
            regions=(),
            changed_pixel_ratio=0.0,
        )
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- REMOVED: tip box at lower right
ISSUES: A tip box is missing."""

        result = parse_response(
            raw,
            model=MODELS["reason2-8b"],
            latency_seconds=1.2345,
            contour=contour,
        )

        self.assertEqual(result.verdict, "FAIL")
        self.assertEqual(result.confidence, "High")
        self.assertEqual(result.issues, "A tip box is missing.")
        self.assertEqual(result.latency_seconds, 1.234)

    def test_marks_unstructured_response_unknown(self):
        contour = ContourResult(
            image=Image.new("RGB", (10, 10)),
            regions=(),
            changed_pixel_ratio=0.0,
        )

        result = parse_response(
            "The images look similar.",
            model=MODELS["reason2-2b"],
            latency_seconds=1.0,
            contour=contour,
        )

        self.assertEqual(result.verdict, "UNKNOWN")
        self.assertEqual(result.confidence, "Unknown")

    def test_parses_baseline_without_contour(self):
        result = parse_response(
            "RESULT: PASS\nCONFIDENCE: High\nCHANGES:\n- None\nISSUES: None",
            model=MODELS["reason2-8b"],
            latency_seconds=0.5,
            contour=None,
            analysis_mode="Baseline",
        )

        self.assertEqual(result.analysis_mode, "Baseline")
        self.assertEqual(result.contour_regions, 0)
        self.assertEqual(result.changes, "- None")

    def test_parses_inline_changes(self):
        result = parse_response(
            "RESULT: PASS\nCONFIDENCE: High\nCHANGES: None\nISSUES: None",
            model=MODELS["reason2-8b"],
            latency_seconds=0.5,
            contour=None,
            analysis_mode="Baseline",
        )

        self.assertEqual(result.changes, "None")


if __name__ == "__main__":
    unittest.main()
