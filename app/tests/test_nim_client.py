import unittest

from PIL import Image

from visual_inspection.config import MODELS
from visual_inspection.nim_client import (
    INSPECTION_SCOPE,
    NANO_BASELINE_PROMPT,
    NANO_CONTOUR_PROMPT,
    REASON2_2B_BASELINE_PROMPT,
    REASON2_2B_CONTOUR_PROMPT,
    REASON2_8B_PROMPT,
    _canonicalize_valid_fail_response,
    _max_tokens_for,
    _normalize_invalid_fail_response,
    _response_rejection_reason,
    _system_prompt_for,
    parse_response,
    prompt_bundle_for,
)
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
            preprocessing_seconds=0.1254,
        )

        self.assertEqual(result.verdict, "FAIL")
        self.assertEqual(result.confidence, "High")
        self.assertEqual(result.issues, "A tip box is missing.")
        self.assertEqual(result.latency_seconds, 1.234)
        self.assertEqual(result.preprocessing_seconds, 0.125)
        self.assertEqual(result.total_seconds, 1.36)

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

    def test_preserves_source_response_separately_from_normalized_scoring_text(self):
        source = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- REMOVED — plate — rear-left carrier
ISSUES: The rear-left carrier is occupied in expected and empty in observed."""
        normalized = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- REMOVED — plate — selected deck region
ISSUES: The expected plate is visible in IMAGE 1 but absent from IMAGE 2."""

        result = parse_response(
            normalized,
            model=MODELS["reason2-8b"],
            latency_seconds=0.5,
            contour=None,
            analysis_mode="Baseline",
            source_response=source,
        )

        self.assertEqual(result.raw_response, source)
        self.assertEqual(result.normalized_response, normalized)
        self.assertEqual(
            result.issues,
            "The expected plate is visible in IMAGE 1 but absent from IMAGE 2.",
        )

    def test_parses_inline_changes(self):
        result = parse_response(
            "RESULT: PASS\nCONFIDENCE: High\nCHANGES: None\nISSUES: None",
            model=MODELS["reason2-8b"],
            latency_seconds=0.5,
            contour=None,
            analysis_mode="Baseline",
        )

        self.assertEqual(result.changes, "None")

    def test_parses_standalone_verdict(self):
        result = parse_response(
            "FAIL\nCONFIDENCE: Low\nCHANGES:\n- ADDED — tool — top left\nISSUES: Tool added.",
            model=MODELS["reason2-2b"],
            latency_seconds=0.5,
            contour=None,
            analysis_mode="Baseline",
        )

        self.assertEqual(result.verdict, "FAIL")

    def test_parses_angle_wrapped_fields(self):
        result = parse_response(
            "RESULT: <PASS>\nCONFIDENCE: <Medium>\nCHANGES:\n- None\nISSUES: None",
            model=MODELS["reason2-8b"],
            latency_seconds=0.5,
            contour=None,
            analysis_mode="Baseline",
        )

        self.assertEqual(result.verdict, "PASS")
        self.assertEqual(result.confidence, "Medium")


class ResponseEvidenceGateTests(unittest.TestCase):
    def test_rejects_human_evidence(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- FOREIGN OBJECT — hand — lower-left deck
ISSUES: A hand appears only in observed."""

        self.assertEqual(
            _response_rejection_reason(raw), "out-of-scope human evidence"
        )

    def test_rejects_placeholder_change_label(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- CHANGE 1
ISSUES: A plate is absent."""

        self.assertEqual(
            _response_rejection_reason(raw), "placeholder change label"
        )

    def test_rejects_fail_without_qualifying_object(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- REPLACED — yellow checkerboard — lower deck
ISSUES: The checkerboard differs."""

        self.assertEqual(
            _response_rejection_reason(raw),
            "FAIL without a qualifying deck-object noun",
        )

    def test_rejects_fail_without_literal_action_label(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- The plate is missing from the selected region.
ISSUES: The expected plate is absent in observed."""

        self.assertEqual(
            _response_rejection_reason(raw),
            "FAIL without a literal action label",
        )

    def test_accepts_grounded_inanimate_deck_change(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- REMOVED — plate — lower-right deck
ISSUES: The expected plate is absent in observed."""

        self.assertIsNone(_response_rejection_reason(raw))

    def test_canonicalizes_valid_fail_explanation_from_action_and_object(self):
        raw = """RESULT: FAIL
CONFIDENCE: Low
CHANGES:
- Removed plate
ISSUES: Expected white tray; observed yellow tray."""

        canonical = _canonicalize_valid_fail_response(raw)

        self.assertIn("- REMOVED — plate — selected deck region", canonical)
        self.assertIn("expected plate", canonical)
        self.assertIn("absent", canonical)
        self.assertNotIn("yellow tray", canonical)

    def test_normalizes_missing_object_to_removed_plate(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- None
ISSUES: The white circular object is missing in the observed image."""

        normalized = _normalize_invalid_fail_response(raw)

        self.assertIn("- REMOVED — plate — selected deck region", normalized)
        self.assertIn(
            "visible in IMAGE 1 but absent from the same deck region in IMAGE 2",
            normalized,
        )
        self.assertIsNone(_response_rejection_reason(normalized))

    def test_normalizes_exposed_gray_carrier_to_removed_plate(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- The white rectangular object was replaced with a gray rectangular object.
ISSUES: The white rectangular object is replaced by a gray carrier."""

        normalized = _normalize_invalid_fail_response(raw)

        self.assertIn("- REMOVED — plate — selected deck region", normalized)

    def test_does_not_normalize_human_evidence(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- A hand appears in observed.
ISSUES: A hand is added."""

        self.assertEqual(_normalize_invalid_fail_response(raw), raw)

    def test_normalizes_pliers_to_foreign_object_tool(self):
        raw = """RESULT: FAIL
CONFIDENCE: High
CHANGES:
- None
ISSUES: FOREIGN OBJECT: A pair of pliers is present only in observed."""

        normalized = _normalize_invalid_fail_response(raw)

        self.assertIn("- FOREIGN OBJECT — tool — selected deck region", normalized)
        self.assertNotIn("human", normalized.lower())

    def test_parses_fenced_json_response(self):
        raw = '''```json
{
  "RESULT": "FAIL",
  "CONFIDENCE": 0.97,
  "CHANGES": "REMOVED plate",
  "ISSUES": "The expected plate is absent in the observed image."
}
```'''

        result = parse_response(
            raw,
            model=MODELS["cosmos3-nano"],
            latency_seconds=0.5,
            contour=None,
            analysis_mode="Baseline",
        )

        self.assertEqual(result.verdict, "FAIL")
        self.assertEqual(result.confidence, "High")
        self.assertEqual(result.changes, "REMOVED plate")
        self.assertEqual(
            result.issues, "The expected plate is absent in the observed image."
        )

    def test_normalizes_inline_numeric_confidence(self):
        result = parse_response(
            "RESULT: PASS\nCONFIDENCE: 0.72\nCHANGES: None\nISSUES: None",
            model=MODELS["cosmos3-nano"],
            latency_seconds=0.5,
            contour=None,
            analysis_mode="Baseline",
        )

        self.assertEqual(result.verdict, "PASS")
        self.assertEqual(result.confidence, "Medium")


class ModelPromptSelectionTests(unittest.TestCase):
    def setUp(self):
        self.contour = ContourResult(
            image=Image.new("RGB", (10, 10)),
            regions=(),
            changed_pixel_ratio=0.0,
        )

    def test_selects_reason2_2b_prompts_and_budget(self):
        model = MODELS["reason2-2b"]

        self.assertEqual(
            _system_prompt_for(model, None),
            f"{REASON2_2B_BASELINE_PROMPT}\n\n{INSPECTION_SCOPE}",
        )
        self.assertEqual(
            _system_prompt_for(model, self.contour),
            f"{REASON2_2B_CONTOUR_PROMPT}\n\n{INSPECTION_SCOPE}",
        )
        self.assertEqual(_max_tokens_for(model), 192)

    def test_selects_reason2_8b_prompts_and_budget(self):
        model = MODELS["reason2-8b"]

        self.assertEqual(
            _system_prompt_for(model, None),
            f"{REASON2_8B_PROMPT}\n\n{INSPECTION_SCOPE}",
        )
        self.assertIn("red boxes", _system_prompt_for(model, self.contour))
        self.assertEqual(_max_tokens_for(model), 384)

    def test_selects_nano_prompts_and_budget(self):
        model = MODELS["cosmos3-nano"]

        self.assertEqual(
            _system_prompt_for(model, None),
            f"{NANO_BASELINE_PROMPT}\n\n{INSPECTION_SCOPE}",
        )
        self.assertEqual(
            _system_prompt_for(model, self.contour),
            f"{NANO_CONTOUR_PROMPT}\n\n{INSPECTION_SCOPE}",
        )
        self.assertEqual(_max_tokens_for(model), 256)

    def test_every_model_and_mode_ignores_people_and_body_parts(self):
        for model in MODELS.values():
            for contour in (None, self.contour):
                with self.subTest(model=model.key, contour=contour is not None):
                    prompt = _system_prompt_for(model, contour)
                    self.assertIn("mask all human content", prompt)
                    self.assertIn("hands, arms, and fingers", prompt)
                    self.assertIn("FAIL is legal only", prompt)
                    self.assertIn("independently resting on", prompt)
                    self.assertIn("colored outlines", prompt)
                    self.assertIn("Never describe masked", prompt)

    def test_prompt_bundle_shows_every_2b_recovery_attempt(self):
        bundle = prompt_bundle_for(
            MODELS["reason2-2b"],
            contour_assisted=False,
        )

        self.assertIn("FULL-FRAME SYSTEM PROMPT", bundle)
        self.assertIn("LOCAL RECOVERY SYSTEM PROMPT", bundle)
        self.assertEqual(bundle.count("LOCAL RECOVERY USER MESSAGE — ATTEMPT"), 8)
        self.assertIn("mask all human content", bundle)

    def test_prompt_bundle_includes_contour_input_and_8b_recovery(self):
        bundle = prompt_bundle_for(
            MODELS["reason2-8b"],
            contour_assisted=True,
        )

        self.assertIn("IMAGE 3 — CONTOUR VIEW: [image payload]", bundle)
        self.assertIn("red boxes", bundle)
        self.assertEqual(bundle.count("LOCAL RECOVERY USER MESSAGE — ATTEMPT"), 3)


if __name__ == "__main__":
    unittest.main()
