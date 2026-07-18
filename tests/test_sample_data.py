"""Tests for the synthetic company generator used in mock mode for demos.

These make sure the generated data is reproducible and actually contains the
variety a realistic demo (and the transform/report code) relies on: the full
schema, terminated staff, data gaps, annualised salaries and the mixed-currency
case in the international departments.
"""

import unittest

from personio_export.sample_data import generate_sample_employees
from personio_export.transform import (
    CSV_COLUMNS,
    build_department_summary,
    build_employee_rows,
)


class GeneratorBasicsTests(unittest.TestCase):
    def test_generates_requested_count(self):
        self.assertEqual(len(generate_sample_employees(250)), 250)

    def test_is_deterministic_for_a_seed(self):
        self.assertEqual(
            generate_sample_employees(100, seed=7),
            generate_sample_employees(100, seed=7),
        )

    def test_different_seeds_produce_different_data(self):
        self.assertNotEqual(
            generate_sample_employees(100, seed=1),
            generate_sample_employees(100, seed=2),
        )

    def test_ids_are_unique_and_sequential(self):
        ids = [e["attributes"]["id"]["value"] for e in generate_sample_employees(50)]
        self.assertEqual(ids, list(range(1, 51)))

    def test_records_use_the_personio_attribute_shape(self):
        record = generate_sample_employees(1)[0]
        self.assertEqual(record["type"], "Employee")
        self.assertIn("value", record["attributes"]["first_name"])


class GeneratorTransformTests(unittest.TestCase):
    def setUp(self):
        # A fixed seed keeps these assertions deterministic.
        self.rows = build_employee_rows(generate_sample_employees(500, seed=42))

    def test_every_row_has_the_full_csv_schema(self):
        for row in self.rows:
            for column in CSV_COLUMNS:
                self.assertIn(column, row)

    def test_contains_terminated_employees(self):
        self.assertTrue(any(r["Termination date"] for r in self.rows))

    def test_contains_data_gaps(self):
        self.assertTrue(any(not r["email"] for r in self.rows), "expected some missing emails")
        self.assertTrue(
            any(r["Base Salary"] == "" for r in self.rows), "expected some missing salaries"
        )

    def test_salaries_are_annualised_numbers(self):
        salaries = [r["Base Salary"] for r in self.rows if isinstance(r["Base Salary"], (int, float))]
        self.assertTrue(salaries)
        # Even a monthly amount, once annualised, is comfortably above 10k.
        self.assertTrue(all(salary > 10000 for salary in salaries))

    def test_international_departments_mix_currencies(self):
        intl = {
            r["_currency"]
            for r in self.rows
            if r["department"] in {"Sales", "Customer Success"}
        }
        self.assertTrue({"GBP", "USD"} & intl, "international teams should include non-EUR pay")

    def test_domestic_departments_stay_single_currency(self):
        engineering = {r["_currency"] for r in self.rows if r["department"] == "Engineering"}
        self.assertEqual(engineering, {"EUR"})

    def test_summary_covers_all_ten_departments(self):
        self.assertEqual(len(build_department_summary(self.rows)), 10)


if __name__ == "__main__":
    unittest.main()
