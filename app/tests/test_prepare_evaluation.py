import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "prepare-workshop-evaluation.py"
SPEC = importlib.util.spec_from_file_location("prepare_workshop_evaluation", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PrepareEvaluationTests(unittest.TestCase):
    def test_reads_first_model_results(self):
        records = [{"ref": "reference.png", "live": "live.png", "label": "FAIL"}]

        self.assertEqual(MODULE.result_records({"reason2-8b": {"results": records}}), records)

    def test_rejects_unknown_shape(self):
        with self.assertRaises(ValueError):
            MODULE.result_records({"metrics": {"n": 7}})


if __name__ == "__main__":
    unittest.main()
