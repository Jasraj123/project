#!/usr/bin/env python3
"""Personio Employee Export - command-line entry point.

Run daily to produce a fresh CSV of employees plus a per-department summary.

Usage:
    python run_export.py                 # uses config.yaml in this folder
    python run_export.py --config path/to/config.yaml
"""

from __future__ import annotations

import argparse
import logging
import sys

from personio_export.client import PersonioAPIError, PersonioClient
from personio_export.config import Config, ConfigError, load_config
from personio_export.exporter import write_employee_csv, write_summary_csv
from personio_export.report import build_run_report, print_run_report
from personio_export.sample_data import get_sample_employees
from personio_export.transform import (
    CSV_COLUMNS,
    SUMMARY_COLUMNS,
    build_department_summary,
    build_employee_rows,
)

logger = logging.getLogger("personio_export")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _get_raw_employees(config: Config) -> list[dict]:
    """Fetch employees from the API, or return sample data in mock mode."""
    if config.use_mock_data:
        logger.info("Running in MOCK mode - using bundled sample data (no API calls).")
        employees = get_sample_employees()
        logger.info("Fetched %d employees", len(employees))
        return employees

    client = PersonioClient(config.base_url, config.client_id, config.client_secret)
    client.authenticate()
    return client.fetch_employees()


def _print_summary(summary_rows: list[dict]) -> None:
    """Print the department summary to the console for a quick glance."""
    print("\nDepartment summary")
    print("-" * 52)
    print(f"{'department':<24}{'count':>8}{'avg base salary':>20}")
    for row in summary_rows:
        avg = row["average_base_salary"]
        avg_text = f"{avg:,.2f}" if isinstance(avg, (int, float)) else "-"
        print(f"{row['department']:<24}{row['employee_count']:>8}{avg_text:>20}")
    print("-" * 52)


def run(config_path: str) -> int:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        logger.error("Configuration problem: %s", exc)
        return 1

    try:
        raw_employees = _get_raw_employees(config)
    except PersonioAPIError as exc:
        logger.error("Could not retrieve data from Personio: %s", exc)
        return 1

    if not raw_employees:
        logger.warning("No employees returned - writing empty output files.")

    employee_rows = build_employee_rows(raw_employees)
    summary_rows = build_department_summary(employee_rows)

    try:
        write_employee_csv(config.output_dir, config.employee_file, CSV_COLUMNS, employee_rows)
        write_summary_csv(config.output_dir, config.summary_file, SUMMARY_COLUMNS, summary_rows)
    except OSError as exc:
        logger.error("Could not write output: %s", exc)
        return 1

    _print_summary(summary_rows)
    print_run_report(build_run_report(employee_rows))
    logger.info("Done.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Personio employees to CSV.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to the YAML config file (default: config.yaml).",
    )
    args = parser.parse_args()

    _setup_logging()
    sys.exit(run(args.config))


if __name__ == "__main__":
    main()
