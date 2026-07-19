"""Sample employee data for mock mode.

Records mirror the Personio v1 response shape so the same transform runs on them.
get_sample_employees() returns a fixed 6-record set (used by tests);
generate_sample_employees() builds a larger seeded synthetic company for demos.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any


def _nested(type_name: str, name: str) -> dict[str, Any]:
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
            # Monthly amount; annualised to 54000 by the transform.
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
        # Terminated employee.
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
        # Employee with several missing fields.
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


# --------------------------------------------------------------------------- #
# Synthetic company generator
# --------------------------------------------------------------------------- #

_EUR_OFFICES = [
    ("Berlin", "EUR"),
    ("Munich", "EUR"),
    ("Madrid", "EUR"),
    ("Amsterdam", "EUR"),
    ("Dublin", "EUR"),
]

# Only the international departments draw from these, so they mix currencies.
_INTERNATIONAL_OFFICES = _EUR_OFFICES + [("London", "GBP"), ("New York", "USD")]
_INTERNATIONAL_DEPARTMENTS = {"Sales", "Customer Success"}

# Department -> its teams and a midpoint annual base salary.
_DEPARTMENTS: dict[str, dict[str, Any]] = {
    "Engineering": {"teams": ["Platform", "Frontend", "Backend", "Data", "SRE"], "base": 72000},
    "Product": {"teams": ["Core", "Growth", "Design"], "base": 78000},
    "Sales": {"teams": ["Outbound", "Inbound", "Enterprise", "SMB"], "base": 55000},
    "Marketing": {"teams": ["Content", "Demand Gen", "Brand"], "base": 52000},
    "Customer Success": {"teams": ["Onboarding", "Support", "Renewals"], "base": 48000},
    "People": {"teams": ["HR Operations", "Talent", "L&D"], "base": 50000},
    "Finance": {"teams": ["Accounting", "FP&A", "Payroll"], "base": 60000},
    "Legal": {"teams": ["Commercial", "Privacy"], "base": 66000},
    "IT": {"teams": ["Helpdesk", "Infrastructure", "Security"], "base": 58000},
    "Operations": {"teams": ["Facilities", "Procurement"], "base": 45000},
}

_POSITIONS = [
    "Associate",
    "Specialist",
    "Senior Specialist",
    "Manager",
    "Senior Manager",
    "Lead",
    "Director",
]

_EMPLOYMENT_TYPES = ["internal", "internal", "internal", "external"]
_WEEKLY_HOURS = ["40", "40", "40", "32", "20"]

_FIRST_NAMES = (
    "Alex Bianca Chen Diana Ewan Farah Georg Hana Ivan Julia Kwame Lena Mateo "
    "Nadia Omar Petra Quentin Rosa Sven Tara Uwe Vera Wassim Xenia Yara Zoltan "
    "Aisha Bruno Carla Dmitri Elif Finn Greta Hugo"
).split()
_LAST_NAMES = (
    "Berg Novak Wu Ferreira Clarke Idris Schmidt Ito Petrov Meier Osei Kaur "
    "Rossi Haddad Khan Novakova Dubois Silva Larsson Nguyen Weber Costa Ali "
    "Popescu Fischer Santos Kowalski Bauer Reyes Andersson"
).split()


def _iso(day: date) -> str:
    return f"{day.isoformat()}T00:00:00+01:00"


def generate_sample_employees(count: int = 2000, seed: int = 42) -> list[dict[str, Any]]:
    """Generate a seeded synthetic company of ``count`` employees.

    Mirrors the Personio v1 shape and mixes departments, currencies, salary
    intervals, terminated staff and some missing fields. The seed makes it
    reproducible.
    """
    rng = random.Random(seed)
    dept_names = list(_DEPARTMENTS)
    today = date.today()

    supervisors = [
        (rng.choice(_FIRST_NAMES), rng.choice(_LAST_NAMES)) for _ in range(max(count // 40, 5))
    ]

    employees: list[dict[str, Any]] = []
    for i in range(1, count + 1):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)

        department = rng.choice(dept_names)
        dept = _DEPARTMENTS[department]
        team = rng.choice(dept["teams"])
        if department in _INTERNATIONAL_DEPARTMENTS:
            office, currency = rng.choice(_INTERNATIONAL_OFFICES)
        else:
            office, currency = rng.choice(_EUR_OFFICES)
        position = rng.choice(_POSITIONS)

        annual = int(dept["base"] * rng.uniform(0.8, 2.3) / 500) * 500
        if rng.random() < 0.25:
            interval = "monthly"
            salary_value: Any = round(annual / 12)
        else:
            interval = "yearly"
            salary_value = annual
        if rng.random() < 0.02:
            salary_value = None
            interval = None

        hire_day = today - timedelta(days=rng.randint(30, 365 * 10))
        terminated = rng.random() < 0.07
        if terminated:
            status = "inactive"
            term_day = hire_day + timedelta(days=rng.randint(90, 365 * 8))
            if term_day > today:
                term_day = today
            termination_date: Any = _iso(term_day)
        else:
            status = "active"
            termination_date = None

        email: Any = None
        if rng.random() >= 0.03:
            email = f"{first}.{last}{i}@example.com".lower()

        team_ref = _nested("Team", team) if rng.random() >= 0.05 else {"value": None}
        if rng.random() >= 0.05:
            sup_first, sup_last = rng.choice(supervisors)
            supervisor_ref: Any = _supervisor(sup_first, sup_last)
        else:
            supervisor_ref = {"value": None}

        last_mod = today - timedelta(days=rng.randint(0, 365))

        employees.append(
            _employee(
                id={"value": i},
                first_name={"value": first},
                last_name={"value": last},
                email={"value": email},
                status={"value": status},
                hire_date={"value": _iso(hire_day)},
                termination_date={"value": termination_date},
                position={"value": f"{position}, {department}"},
                department=_nested("Department", department),
                team=team_ref,
                supervisor=supervisor_ref,
                office=_nested("Office", office),
                weekly_working_hours={"value": rng.choice(_WEEKLY_HOURS)},
                employment_type={"value": rng.choice(_EMPLOYMENT_TYPES)},
                cost_centers={"value": [{"attributes": {"name": f"CC-{department}"}}]},
                fix_salary={"value": salary_value},
                fix_salary_interval={"value": interval},
                fix_salary_currency={"value": currency},
                last_modified_at={"value": _iso(last_mod)},
            )
        )

    return employees
