"""Bundled sample employees used when use_mock_data is true.

The structure intentionally mirrors the real Personio v1 Employee response
(nested {"label", "value"} attributes) so the same transform logic works
against live data without changes. It includes a terminated employee and some
missing fields on purpose, to show how those cases are handled.
"""

from __future__ import annotations

from typing import Any


def _nested(type_name: str, name: str) -> dict[str, Any]:
    """Build a nested reference object (department, team, office, ...)."""
    return {"value": {"type": type_name, "attributes": {"name": name}}}


def _supervisor(first: str, last: str) -> dict[str, Any]:
    return {
        "value": {
            "type": "Employee",
            "attributes": {
                "first_name": {"value": first},
                "last_name": {"value": last},
            },
        }
    }


def _employee(**attributes: Any) -> dict[str, Any]:
    # All sample offices are in the euro zone, so default the salary currency to
    # EUR (mirrors the real API, which returns fix_salary_currency per employee).
    attributes.setdefault("fix_salary_currency", {"value": "EUR"})
    return {"type": "Employee", "attributes": attributes}


def get_sample_employees() -> list[dict[str, Any]]:
    return [
        _employee(
            id={"value": 1},
            first_name={"value": "Alex"},
            last_name={"value": "Berg"},
            email={"value": "alex.berg@example.com"},
            status={"value": "active"},
            hire_date={"value": "2021-05-01T00:00:00+02:00"},
            termination_date={"value": None},
            position={"value": "Backend Engineer"},
            department=_nested("Department", "Engineering"),
            team=_nested("Team", "Platform"),
            supervisor=_supervisor("Dana", "Lee"),
            office=_nested("Office", "Berlin"),
            weekly_working_hours={"value": "40"},
            employment_type={"value": "internal"},
            cost_centers={"value": [{"attributes": {"name": "CC-Engineering"}}]},
            fix_salary={"value": 68000},
            fix_salary_interval={"value": "yearly"},
            last_modified_at={"value": "2024-11-03T09:15:00+01:00"},
        ),
        _employee(
            id={"value": 2},
            first_name={"value": "Bianca"},
            last_name={"value": "Novak"},
            email={"value": "bianca.novak@example.com"},
            status={"value": "active"},
            hire_date={"value": "2019-09-16T00:00:00+02:00"},
            termination_date={"value": None},
            position={"value": "Engineering Manager"},
            department=_nested("Department", "Engineering"),
            team=_nested("Team", "Platform"),
            supervisor=_supervisor("Carlos", "Mendez"),
            office=_nested("Office", "Berlin"),
            weekly_working_hours={"value": "40"},
            employment_type={"value": "internal"},
            cost_centers={"value": [{"attributes": {"name": "CC-Engineering"}}]},
            fix_salary={"value": 92000},
            fix_salary_interval={"value": "yearly"},
            last_modified_at={"value": "2024-10-21T14:02:00+02:00"},
        ),
        _employee(
            id={"value": 3},
            first_name={"value": "Chen"},
            last_name={"value": "Wu"},
            email={"value": "chen.wu@example.com"},
            status={"value": "active"},
            hire_date={"value": "2022-01-10T00:00:00+01:00"},
            termination_date={"value": None},
            position={"value": "People Partner"},
            department=_nested("Department", "People"),
            team=_nested("Team", "HR Operations"),
            supervisor=_supervisor("Dana", "Lee"),
            office=_nested("Office", "Munich"),
            weekly_working_hours={"value": "32"},
            employment_type={"value": "internal"},
            cost_centers={"value": [{"attributes": {"name": "CC-People"}}]},
            # Stored monthly in Personio; the export normalises this to 54000/year.
            fix_salary={"value": 4500},
            fix_salary_interval={"value": "monthly"},
            last_modified_at={"value": "2024-09-30T11:45:00+02:00"},
        ),
        _employee(
            id={"value": 4},
            first_name={"value": "Diana"},
            last_name={"value": "Ferreira"},
            email={"value": "diana.ferreira@example.com"},
            status={"value": "active"},
            hire_date={"value": "2023-03-01T00:00:00+01:00"},
            termination_date={"value": None},
            position={"value": "Sales Development Rep"},
            department=_nested("Department", "Sales"),
            team=_nested("Team", "Outbound"),
            supervisor=_supervisor("Erik", "Sund"),
            office=_nested("Office", "Dublin"),
            weekly_working_hours={"value": "40"},
            employment_type={"value": "internal"},
            cost_centers={"value": [{"attributes": {"name": "CC-Sales"}}]},
            fix_salary={"value": 46000},
            fix_salary_interval={"value": "yearly"},
            last_modified_at={"value": "2024-11-01T08:00:00+01:00"},
        ),
        # Terminated employee - shows Termination date populated.
        _employee(
            id={"value": 5},
            first_name={"value": "Ewan"},
            last_name={"value": "Clarke"},
            email={"value": "ewan.clarke@example.com"},
            status={"value": "inactive"},
            hire_date={"value": "2018-07-02T00:00:00+02:00"},
            termination_date={"value": "2024-06-30T00:00:00+02:00"},
            position={"value": "Account Executive"},
            department=_nested("Department", "Sales"),
            team=_nested("Team", "Enterprise"),
            supervisor=_supervisor("Erik", "Sund"),
            office=_nested("Office", "Dublin"),
            weekly_working_hours={"value": "40"},
            employment_type={"value": "internal"},
            cost_centers={"value": [{"attributes": {"name": "CC-Sales"}}]},
            fix_salary={"value": 61000},
            fix_salary_interval={"value": "yearly"},
            last_modified_at={"value": "2024-07-01T16:30:00+02:00"},
        ),
        # Employee with several missing fields - shows blanks are handled safely.
        _employee(
            id={"value": 6},
            first_name={"value": "Farah"},
            last_name={"value": "Idris"},
            email={"value": "farah.idris@example.com"},
            status={"value": "active"},
            hire_date={"value": "2024-02-19T00:00:00+01:00"},
            termination_date={"value": None},
            position={"value": "Working Student"},
            department=_nested("Department", "People"),
            team={"value": None},
            supervisor={"value": None},
            office=_nested("Office", "Munich"),
            weekly_working_hours={"value": "20"},
            employment_type={"value": "internal"},
            cost_centers={"value": []},
            fix_salary={"value": None},
            fix_salary_interval={"value": None},
            last_modified_at={"value": "2024-08-12T10:05:00+02:00"},
        ),
    ]
