import unittest

from visual_inspection.evaluation import calculate_metrics


class EvaluationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
