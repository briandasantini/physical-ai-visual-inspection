import unittest

from visual_inspection.tutorial import TUTORIAL_STEPS, progress_summary


class TutorialProgressTests(unittest.TestCase):
    def test_empty_progress_points_to_first_gate(self):
        summary = progress_summary([])

        self.assertIn("0/8 (0%)", summary)
        self.assertIn(TUTORIAL_STEPS[0], summary)

    def test_complete_progress_reports_completion(self):
        summary = progress_summary(TUTORIAL_STEPS)

        self.assertIn("Tutorial complete", summary)


if __name__ == "__main__":
    unittest.main()
