import unittest

from visual_inspection.evaluation import calculate_metrics, score_semantics


class EvaluationTests(unittest.TestCase):
    def test_removed_does_not_match_moved_action(self):
        record = {
            "pair_id": "evaluation-shift",
            "category": "Shift/Displace",
            "error_type": "Shifted labware",
            "expected": "FAIL",
            "verdict": "FAIL",
            "changes": "- REMOVED — plate — selected deck region",
            "issues": "The expected plate is absent from the same deck region.",
        }

        scored = score_semantics(record)

        self.assertEqual(scored["expected_action"], "MOVED")
        self.assertFalse(scored["action_correct"])

    def test_calculates_fail_as_positive_class(self):
        metrics = calculate_metrics(
            [
                {"expected": "FAIL", "verdict": "FAIL"},
                {"expected": "FAIL", "verdict": "PASS"},
                {"expected": "PASS", "verdict": "FAIL"},
                {"expected": "PASS", "verdict": "PASS"},
            ]
        )

        self.assertEqual(metrics["accuracy"], 0.5)
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertEqual(metrics["f1"], 0.5)

    def test_scores_action_item_and_latency(self):
        metrics = calculate_metrics(
            [
                {
                    "pair_id": "r1_cd006",
                    "expected": "FAIL",
                    "verdict": "FAIL",
                    "changes": "REMOVED — yellow plate — lower right",
                    "issues": "A plate is missing.",
                    "latency_seconds": 2.0,
                    "preprocessing_seconds": 0.2,
                    "total_seconds": 2.2,
                },
                {
                    "pair_id": "r1_pliers",
                    "expected": "FAIL",
                    "verdict": "PASS",
                    "changes": "None",
                    "issues": "None",
                    "latency_seconds": 4.0,
                    "preprocessing_seconds": 0.0,
                    "total_seconds": 4.0,
                },
            ]
        )

        self.assertEqual(metrics["action_accuracy"], 1.0)
        self.assertEqual(metrics["action_total"], 1)
        self.assertEqual(metrics["item_accuracy"], 1.0)
        self.assertEqual(metrics["avg_nim_seconds"], 3.0)
        self.assertEqual(metrics["avg_preprocessing_seconds"], 0.1)
        self.assertEqual(metrics["avg_total_seconds"], 3.1)
        self.assertEqual(metrics["p95_total_seconds"], 4.0)

    def test_semantics_are_not_scored_for_pass_prediction(self):
        scores = score_semantics(
            {
                "pair_id": "r1_tilt",
                "expected": "FAIL",
                "verdict": "PASS",
                "changes": "None",
                "issues": "None",
            }
        )

        self.assertIsNone(scores["action_correct"])
        self.assertIsNone(scores["item_correct"])


if __name__ == "__main__":
    unittest.main()
