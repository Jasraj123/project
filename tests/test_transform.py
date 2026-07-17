"""Unit tests for the transform logic (the trickiest part of the tool).

Run with either:
    python -m unittest
    pytest
"""

import logging
import unittest

from personio_export.transform import (
    _annual_base_salary,
    _date_only,
    _supervisor_name,
    build_department_summary,
    build_employee_rows,
)


def _attr(value):
    """Wrap a value the way the Personio API does: {"value": ...}."""
    return {"value": value}


def _ref(name):
    """A nested reference object (department/team/office/...)."""
    return {"value": {"attributes": {"name": name}}}


class DateFormattingTests(unittest.TestCase):
    def test_timestamp_is_trimmed_to_date(self):
        self.assertEqual(_date_only(_attr("2021-05-01T00:00:00+02:00")), "2021-05-01")

    def test_missing_date_is_blank(self):
        self.assertEqual(_date_only(_attr(None)), "")
        self.assertEqual(_date_only(None), "")


class SupervisorNameTests(unittest.TestCase):
    def test_first_and_last_are_joined(self):
        supervisor = {
            "value": {"attributes": {"first_name": _attr("Dana"), "last_name": _attr("Lee")}}
        }
        self.assertEqual(_supervisor_name(supervisor), "Dana Lee")

    def test_missing_supervisor_is_blank(self):
        self.assertEqual(_supervisor_name(_attr(None)), "")


class SalaryNormalizationTests(unittest.TestCase):
    def test_monthly_is_annualised(self):
        self.assertEqual(_annual_base_salary(_attr(4500), _attr("monthly")), 54000.0)

    def test_yearly_is_unchanged(self):
        self.assertEqual(_annual_base_salary(_attr(54000), _attr("yearly")), 54000.0)

    def test_weekly_is_annualised(self):
        self.assertEqual(_annual_base_salary(_attr(1000), _attr("weekly")), 52000.0)

    def test_unknown_interval_is_treated_as_annual(self):
        self.assertEqual(_annual_base_salary(_attr(60000), _attr("fortnightly")), 60000.0)

    def test_missing_interval_is_treated_as_annual(self):
        self.assertEqual(_annual_base_salary(_attr(60000), _attr(None)), 60000.0)

    def test_missing_salary_is_none(self):
        self.assertIsNone(_annual_base_salary(_attr(None), _attr("monthly")))

    def test_row_uses_interval(self):
        record = {
            "type": "Employee",
            "attributes": {
                "id": _attr(1),
                "fix_salary": _attr(4500),
                "fix_salary_interval": _attr("monthly"),
            },
        }
        row = build_employee_rows([record])[0]
        self.assertEqual(row["Base Salary"], 54000.0)


class EmployeeRowTests(unittest.TestCase):
    def _sample_record(self):
        return {
            "type": "Employee",
            "attributes": {
                "id": _attr(1),
                "first_name": _attr("Alex"),
                "last_name": _attr("Berg"),
                "email": _attr("alex@example.com"),
                "status": _attr("active"),
                "hire_date": _attr("2021-05-01T00:00:00+02:00"),
                "termination_date": _attr(None),
                "position": _attr("Engineer"),
                "department": _ref("Engineering"),
                "team": _ref("Platform"),
                "office": _ref("Berlin"),
                "weekly_working_hours": _attr("40"),
                "employment_type": _attr("internal"),
                "cost_centers": _attr([{"attributes": {"name": "CC-Eng"}}]),
                "fix_salary": _attr(68000),
                "last_modified_at": _attr("2024-11-03T09:15:00+01:00"),
            },
        }

    def test_row_maps_all_columns(self):
        row = build_employee_rows([self._sample_record()])[0]
        self.assertEqual(row["employeeID"], "1")
        self.assertEqual(row["email"], "alex@example.com")
        self.assertEqual(row["Hire date"], "2021-05-01")
        self.assertEqual(row["department"], "Engineering")
        self.assertEqual(row["Cost center"], "CC-Eng")
        self.assertEqual(row["Base Salary"], 68000.0)

    def test_missing_fields_become_blank(self):
        record = {"type": "Employee", "attributes": {"id": _attr(9)}}
        row = build_employee_rows([record])[0]
        self.assertEqual(row["employeeID"], "9")
        self.assertEqual(row["email"], "")
        self.assertEqual(row["department"], "")
        self.assertEqual(row["Base Salary"], "")

    def test_legacy_fixed_salary_key_still_works(self):
        record = self._sample_record()
        del record["attributes"]["fix_salary"]
        record["attributes"]["fixed_salary"] = _attr(50000)
        row = build_employee_rows([record])[0]
        self.assertEqual(row["Base Salary"], 50000.0)


class DepartmentSummaryTests(unittest.TestCase):
    def test_counts_and_average_salary(self):
        rows = [
            {"department": "Sales", "Base Salary": 40000.0},
            {"department": "Sales", "Base Salary": 60000.0},
            {"department": "People", "Base Salary": 50000.0},
        ]
        summary = {r["department"]: r for r in build_department_summary(rows)}
        self.assertEqual(summary["Sales"]["employee_count"], 2)
        self.assertEqual(summary["Sales"]["average_base_salary"], 50000.0)
        self.assertEqual(summary["People"]["employee_count"], 1)

    def test_blank_salary_excluded_from_average(self):
        rows = [
            {"department": "Sales", "Base Salary": 60000.0},
            {"department": "Sales", "Base Salary": ""},
        ]
        summary = build_department_summary(rows)[0]
        # Two people counted, but the average uses only the one real salary.
        self.assertEqual(summary["employee_count"], 2)
        self.assertEqual(summary["average_base_salary"], 60000.0)

    def test_missing_department_is_grouped(self):
        rows = [{"department": "", "Base Salary": ""}]
        summary = build_department_summary(rows)[0]
        self.assertEqual(summary["department"], "(no department)")
        self.assertEqual(summary["average_base_salary"], "")

    def test_mixed_currency_department_warns(self):
        rows = [
            {"department": "Sales", "Base Salary": 60000.0, "_currency": "EUR"},
            {"department": "Sales", "Base Salary": 50000.0, "_currency": "GBP"},
        ]
        with self.assertLogs("personio_export.transform", level="WARNING") as logs:
            build_department_summary(rows)
        self.assertTrue(any("mixes salary currencies" in m for m in logs.output))

    def test_single_currency_department_does_not_warn(self):
        rows = [
            {"department": "Sales", "Base Salary": 60000.0, "_currency": "EUR"},
            {"department": "Sales", "Base Salary": 50000.0, "_currency": "EUR"},
        ]
        logger = logging.getLogger("personio_export.transform")
        with self.assertLogs(logger, level="WARNING") as logs:
            # Emit one record so assertLogs has something even if no warning fires.
            logger.warning("sentinel")
            build_department_summary(rows)
        self.assertFalse(any("mixes salary currencies" in m for m in logs.output))


if __name__ == "__main__":
    unittest.main()
