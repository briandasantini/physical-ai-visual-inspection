import unittest

from visual_inspection.tutorial import PHASES, WORKSHOP_LOOP


class TutorialContentTests(unittest.TestCase):
    def test_loop_describes_discovery_instead_of_prediction(self):
        self.assertIn("inspect what the model saw or invented", WORKSHOP_LOOP)
        self.assertNotIn("Write the expected", WORKSHOP_LOOP)

    def test_phases_have_no_times_and_cover_product_questions(self):
        self.assertTrue(all(len(phase) == 2 for phase in PHASES))
        descriptions = " ".join(description for _, description in PHASES)

        self.assertIn("false-positive versus false-negative", descriptions)
        self.assertIn("missing cases", descriptions)
        self.assertNotIn("minutes", descriptions)


if __name__ == "__main__":
    unittest.main()
