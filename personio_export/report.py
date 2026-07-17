"""Build a short run summary and data-quality report.

After every export we tell the user how many records were processed and flag any
gaps in the data (missing email, department or salary). This gives a customer
confidence in each run and makes problems easy to spot early.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RunReport:
    total: int
    active: int
    inactive: int
    terminated: int
    missing_email: int
    missing_department: int
    missing_salary: int


def build_run_report(rows: list[dict[str, Any]]) -> RunReport:
    """Count totals and data-quality gaps across the exported rows."""
    total = len(rows)
    active = sum(1 for r in rows if str(r.get("status", "")).lower() == "active")
    inactive = total - active
    terminated = sum(1 for r in rows if r.get("Termination date"))
    missing_email = sum(1 for r in rows if not r.get("email"))
    missing_department = sum(1 for r in rows if not r.get("department"))
    missing_salary = sum(1 for r in rows if r.get("Base Salary") in ("", None))

    return RunReport(
        total=total,
        active=active,
        inactive=inactive,
        terminated=terminated,
        missing_email=missing_email,
        missing_department=missing_department,
        missing_salary=missing_salary,
    )


def print_run_report(report: RunReport) -> None:
    """Print the run summary; warn (don't fail) when data gaps are found."""
    print("\nRun summary")
    print("-" * 52)
    print(f"  Employees exported : {report.total}")
    print(f"  Active / inactive  : {report.active} / {report.inactive}")
    print(f"  Terminated (dated) : {report.terminated}")
    print(f"  Missing email      : {report.missing_email}")
    print(f"  Missing department : {report.missing_department}")
    print(f"  Missing base salary: {report.missing_salary}")
    print("-" * 52)

    gaps = report.missing_email + report.missing_department + report.missing_salary
    if gaps:
        logger.warning(
            "Data quality: %d field(s) missing across the export "
            "(%d email, %d department, %d salary). Review the CSV before use.",
            gaps,
            report.missing_email,
            report.missing_department,
            report.missing_salary,
        )
    else:
        logger.info("Data quality: no missing email, department or salary values.")
