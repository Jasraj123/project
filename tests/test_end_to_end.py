"""End-to-end smoke test: run the whole pipeline in mock mode."""

import csv
import os
import tempfile
import unittest

import yaml

from personio_export.transform import CSV_COLUMNS, SUMMARY_COLUMNS
from run_export import run


class EndToEndMockTests(unittest.TestCase):
    def test_run_produces_both_csv_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = os.path.join(tmp, "output")
            config_path = os.path.join(tmp, "config.yaml")
            with open(config_path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    {
                        "personio": {"base_url": "https://api.personio.de"},
                        "export": {"output_dir": output_dir},
                        "use_mock_data": True,
                    },
                    handle,
                )

            exit_code = run(config_path)
            self.assertEqual(exit_code, 0)

            employee_csv = os.path.join(output_dir, "personio_employee_export.csv")
            summary_csv = os.path.join(output_dir, "department_summary.csv")
            self.assertTrue(os.path.exists(employee_csv))
            self.assertTrue(os.path.exists(summary_csv))

            with open(employee_csv, newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_COLUMNS)
                rows = list(reader)
            self.assertEqual(len(rows), 6)
            self.assertNotIn("_currency", rows[0])

            with open(summary_csv, newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)

    def test_missing_config_returns_error_code(self):
        self.assertEqual(run("/nonexistent/path/config.yaml"), 1)


if __name__ == "__main__":
    unittest.main()
