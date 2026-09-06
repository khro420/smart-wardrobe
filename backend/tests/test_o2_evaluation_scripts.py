"""Fail-closed tests for O2 dataset/evaluation orchestration."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from scripts import evaluate_vtoff_paired
from scripts import prepare_dresscode_vtoff_evaluation


class O2EvaluationScriptTests(unittest.TestCase):
    def _dresscode_fixture(self, root: Path) -> None:
        for group in ("upper_body", "lower_body", "dresses"):
            images = root / group / "images"
            images.mkdir(parents=True)
            Image.new("RGB", (24, 32), "navy").save(images / "000001_0.jpg")
            Image.new("RGB", (24, 32), "white").save(images / "000001_1.jpg")
            (root / group / "test_pairs_paired.txt").write_text("000001_0.jpg 000001_1.jpg\n", encoding="utf-8")

    def test_dresscode_audit_requires_license_confirmation(self):
        with tempfile.TemporaryDirectory(prefix="dresscode-audit-") as temporary:
            root = Path(temporary)
            self._dresscode_fixture(root)
            with patch.object(sys, "argv", ["prepare", "--dataset-root", str(root)]), patch.object(prepare_dresscode_vtoff_evaluation, "_persist") as persist:
                with self.assertRaisesRegex(RuntimeError, "license-confirmed"):
                    prepare_dresscode_vtoff_evaluation.main()
                self.assertEqual(persist.call_args.args[0]["status"], "blocked")

    def test_dresscode_audit_reads_only_three_paired_test_groups(self):
        with tempfile.TemporaryDirectory(prefix="dresscode-audit-") as temporary:
            root = Path(temporary)
            self._dresscode_fixture(root)
            with patch.object(sys, "argv", ["prepare", "--dataset-root", str(root), "--license-confirmed"]), patch.object(prepare_dresscode_vtoff_evaluation, "_persist") as persist:
                prepare_dresscode_vtoff_evaluation.main()
            payload = persist.call_args.args[0]
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["paired_examples"], 3)
            self.assertEqual({pair["garment_group"] for pair in payload["pairs"]}, {"upper_body", "lower_body", "dresses"})
            self.assertEqual(payload["training_files_read"], 0)
            self.assertEqual(payload["files_redistributed"], 0)

    def test_category_sampler_requires_and_returns_each_group(self):
        pairs = [
            {"id": f"{group}-{index}", "garment_group": group}
            for group in evaluate_vtoff_paired.GROUP_CATEGORIES
            for index in range(4)
        ]
        sampled = evaluate_vtoff_paired._sample_groups(pairs, 2, 123)
        self.assertEqual(len(sampled), 6)
        self.assertEqual(
            {group: sum(pair["garment_group"] == group for pair in sampled) for group in evaluate_vtoff_paired.GROUP_CATEGORIES},
            {"upper_body": 2, "lower_body": 2, "dresses": 2},
        )
        with self.assertRaisesRegex(RuntimeError, "3 requested"):
            evaluate_vtoff_paired._sample_groups([pair for pair in pairs if pair["garment_group"] != "dresses"], 3, 123)


if __name__ == "__main__":
    unittest.main()
