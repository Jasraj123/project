"""Turn raw Personio employee records into clean, flat rows for CSV output.

Two outputs are produced:
  1. One row per employee, matching the agreed CSV schema.
  2. A per-department summary (headcount and average base salary).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# CSV columns in the exact order required by the export schema.
CSV_COLUMNS = [
    "employeeID",
    "First name",
    "Last name",
    "email",
    "status",
    "Hire date",
    "Termination date",
    "position",
    "department",
    "team",
    "Supervisor name",
    "location",
    "Weekly working hours",
    "Employment type",
    "Cost center",
    "Base Salary",
    "Last modified",
]

SUMMARY_COLUMNS = ["department", "employee_count", "average_base_salary"]


def _value(attribute: Any) -> Any:
    """Return the inner 'value' of a Personio attribute, or the value itself."""
    if isinstance(attribute, dict):
        return attribute.get("value")
    return attribute


def _nested_name(attribute: Any) -> str:
    """Read the 'name' from a nested reference (department/team/office/...)."""
    value = _value(attribute)
    if isinstance(value, dict):
        return str(value.get("attributes", {}).get("name") or "")
    return ""


def _supervisor_name(attribute: Any) -> str:
    """Build 'First Last' from a nested supervisor employee object."""
    value = _value(attribute)
    if not isinstance(value, dict):
        return ""
    attrs = value.get("attributes", {})
    first = _value(attrs.get("first_name")) or ""
    last = _value(attrs.get("last_name")) or ""
    return f"{first} {last}".strip()


def _cost_center_name(attribute: Any) -> str:
    """Cost centers come back as a list; use the first one's name."""
    value = _value(attribute)
    if isinstance(value, list) and value:
        return str(value[0].get("attributes", {}).get("name") or "")
    return ""


def _date_only(attribute: Any) -> str:
    """Normalise a Personio date/timestamp to YYYY-MM-DD (blank if missing)."""
    value = _value(attribute)
    if not value:
        return ""
    return str(value)[:10]


def _text(attribute: Any) -> str:
    """Return a stripped string, or blank if the value is missing."""
    value = _value(attribute)
    if value is None:
        return ""
    return str(value).strip()


def _base_salary(attribute: Any) -> float | None:
    """Return the raw base salary as a number, or None if not set."""
    value = _value(attribute)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("Could not parse base salary '%s'; leaving it blank.", value)
        return None


# Multipliers to convert a Personio salary interval to an annual gross figure.
# Personio stores the amount in `fix_salary` and the period in `fix_salary_interval`.
_ANNUAL_FACTOR = {"yearly": 1, "annually": 1, "annual": 1, "monthly": 12, "weekly": 52}


def _annual_base_salary(salary_attr: Any, interval_attr: Any) -> float | None:
    """Normalise base salary to a yearly figure so departments are comparable.

    Personio returns monthly amounts for most employees but yearly for some, so a
    raw average would mix periods. We convert everything to annual gross using the
    `fix_salary_interval` field; an unknown/blank interval is assumed to be annual.
    """
    amount = _base_salary(salary_attr)
    if amount is None:
        return None

    interval = _text(interval_attr).lower()
    factor = _ANNUAL_FACTOR.get(interval)
    if factor is None:
        if interval:
            logger.warning("Unknown salary interval '%s'; treating amount as annual.", interval)
        factor = 1
    return round(amount * factor, 2)


def build_employee_rows(raw_employees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map each raw employee record to a flat dict keyed by CSV column."""
    rows: list[dict[str, Any]] = []

    for record in raw_employees:
        attrs = record.get("attributes", {})
        # Personio's v1 attribute is "fix_salary"; keep "fixed_salary" as a fallback.
        # Normalise to an annual figure using the salary interval so the column and
        # the department averages are comparable across employees.
        salary = _annual_base_salary(
            attrs.get("fix_salary") or attrs.get("fixed_salary"),
            attrs.get("fix_salary_interval") or attrs.get("salary_interval"),
        )
        currency = _text(attrs.get("fix_salary_currency") or attrs.get("salary_currency"))

        rows.append(
            {
                "employeeID": _text(attrs.get("id")),
                "First name": _text(attrs.get("first_name")),
                "Last name": _text(attrs.get("last_name")),
                "email": _text(attrs.get("email")),
                "status": _text(attrs.get("status")),
                "Hire date": _date_only(attrs.get("hire_date")),
                "Termination date": _date_only(attrs.get("termination_date")),
                "position": _text(attrs.get("position")),
                "department": _nested_name(attrs.get("department")),
                "team": _nested_name(attrs.get("team")),
                "Supervisor name": _supervisor_name(attrs.get("supervisor")),
                "location": _nested_name(attrs.get("office")),
                "Weekly working hours": _text(attrs.get("weekly_working_hours")),
                "Employment type": _text(attrs.get("employment_type")),
                "Cost center": _cost_center_name(attrs.get("cost_centers")),
                "Base Salary": "" if salary is None else salary,
                "Last modified": _date_only(attrs.get("last_modified_at")),
                # Not part of the CSV schema; kept so the summary can detect a
                # department whose salaries mix currencies. Ignored on CSV write.
                "_currency": currency,
            }
        )

    logger.info("Transformed %d employee records", len(rows))
    return rows


def build_department_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate headcount and average base salary per department."""
    totals: dict[str, dict[str, Any]] = {}

    for row in rows:
        department = row["department"] or "(no department)"
        bucket = totals.setdefault(
            department, {"count": 0, "salary_sum": 0.0, "salary_n": 0, "currencies": set()}
        )
        bucket["count"] += 1

        salary = row["Base Salary"]
        if isinstance(salary, (int, float)):
            bucket["salary_sum"] += salary
            bucket["salary_n"] += 1

        currency = row.get("_currency")
        if currency:
            bucket["currencies"].add(currency)

    summary: list[dict[str, Any]] = []
    for department in sorted(totals):
        bucket = totals[department]

        currencies = bucket["currencies"]
        if len(currencies) > 1:
            logger.warning(
                "Department '%s' mixes salary currencies (%s); its average base salary "
                "combines different currencies and should be interpreted with care.",
                department,
                ", ".join(sorted(currencies)),
            )

        average = round(bucket["salary_sum"] / bucket["salary_n"], 2) if bucket["salary_n"] else ""
        summary.append(
            {
                "department": department,
                "employee_count": int(bucket["count"]),
                "average_base_salary": average,
            }
        )

    logger.info("Built department summary for %d departments", len(summary))
    return summary
