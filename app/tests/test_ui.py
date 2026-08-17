import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from visual_inspection.ui import (
    _jupyter_url,
    _select_workshop_tab,
    build_demo,
    inspect_batch_row,
)


class JupyterLinkTests(unittest.TestCase):
    def test_explicit_jupyter_url_wins(self):
        with patch.dict(
            "os.environ",
            {
                "VISUAL_INSPECTION_JUPYTER_URL": "https://terminal.example/lab",
                "BREV_ENV_ID": "ignored",
            },
            clear=True,
        ):
            self.assertEqual(_jupyter_url(), "https://terminal.example/lab")

    def test_brev_environment_id_builds_jupyter_url(self):
        with patch.dict("os.environ", {"BREV_ENV_ID": "abc123"}, clear=True):
            self.assertEqual(
                _jupyter_url(),
                "https://jupyter-abc123.apps.run.brev.nvidia.com/lab",
            )


class WorkshopNavigationTests(unittest.TestCase):
    def test_phase_navigation_selects_requested_tab(self):
        self.assertEqual(_select_workshop_tab("larger-set").selected, "larger-set")

    def test_guide_has_clickable_phases_without_times(self):
        config = str(build_demo().config)

        self.assertIn("check a lab deck before an experiment starts", config)
        self.assertNotIn("Establish a baseline, inspect the misses", config)
        self.assertNotIn("The loop:", config)
        self.assertIn("3 · Agent experiment", config)
        self.assertIn("Open the full documented workshop guide", config)
        self.assertIn("guide-docs-link", config)
        self.assertIn("Dataset reference label", config)
        self.assertNotIn("NVIDIA Cosmos vision-language models", config)
        self.assertNotIn("Optional: use Cursor", config)
        self.assertNotIn("Optional Cosmos3 Nano", config)
        self.assertNotIn("record before running", config)
        self.assertNotIn("25 minutes", config)
        self.assertNotIn("35 minutes", config)
        self.assertNotIn("30 minutes", config)
        self.assertIn("first-examples", config)
        self.assertIn("larger-set", config)
        self.assertIn("explore", config)


class LargerSetSelectionTests(unittest.TestCase):
    def test_selected_row_returns_images_semantics_responses_and_prompt_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            reference_path = Path(directory) / "reference.png"
            observed_path = Path(directory) / "observed.png"
            Image.new("RGB", (20, 10), "white").save(reference_path)
            Image.new("RGB", (20, 10), "gray").save(observed_path)
            evidence = {
                "records": [
                    {
                        "pair_id": "pair-1",
                        "analysis_mode": "Contour-assisted",
                        "scene": "Scene 1",
                        "category": "Shift/Displace",
                        "error_type": "Shifted plate",
                        "expected": "FAIL",
                        "verdict": "FAIL",
                        "expected_action": "MOVED",
                        "action_correct": False,
                        "expected_item": "plate",
                        "item_correct": True,
                        "confidence": "High",
                        "latency_seconds": 1.2,
                        "preprocessing_seconds": 0.1,
                        "total_seconds": 1.3,
                        "issues": "Normalized scoring issue.",
                        "raw_response": "ORIGINAL MODEL RESPONSE",
                        "normalized_response": "NORMALIZED RESPONSE",
                        "model": "Cosmos Reason2 8B",
                        "reference": str(reference_path),
                        "live": str(observed_path),
                    }
                ]
            }

            outputs = inspect_batch_row(evidence, SimpleNamespace(index=(0, 3)))

        reference, observed, detail, raw, normalized, prompt = outputs
        self.assertEqual(reference.size, (20, 10))
        self.assertEqual(observed.size, (20, 10))
        self.assertIn("Action grounded:** No", detail)
        self.assertIn("Object grounded:** Yes", detail)
        self.assertEqual(raw, "ORIGINAL MODEL RESPONSE")
        self.assertEqual(normalized, "NORMALIZED RESPONSE")
        self.assertIn("IMAGE 3 — CONTOUR VIEW", prompt)
        self.assertIn("LOCAL RECOVERY SYSTEM PROMPT", prompt)


if __name__ == "__main__":
    unittest.main()
