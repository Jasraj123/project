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
import os
import sys

from personio_export.client import PersonioAPIError, PersonioClient
from personio_export.config import Config, ConfigError, load_config
from personio_export.delivery import DeliveryError, deliver
from personio_export.documents import (
    DOCUMENT_MANIFEST_COLUMNS,
    DocumentAPIError,
    authenticate_v2,
    build_document_manifest,
    fetch_all_document_metadata,
)
from personio_export.exporter import (
    write_documents_manifest,
    write_employee_csv,
    write_summary_csv,
)
from personio_export.report import build_run_report, print_run_report
from personio_export.sample_data import generate_sample_employees, get_sample_employees
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
    if config.use_mock_data:
        if config.mock_employee_count > 0:
            logger.info(
                "Running in MOCK mode - generating %d synthetic employees (no API calls).",
                config.mock_employee_count,
            )
            employees = generate_sample_employees(config.mock_employee_count)
        else:
            logger.info("Running in MOCK mode - using bundled sample data (no API calls).")
            employees = get_sample_employees()
        logger.info("Fetched %d employees", len(employees))
        return employees

    client = PersonioClient(config.base_url, config.client_id, config.client_secret)
    client.authenticate()
    return client.fetch_employees()


def _export_documents(config: Config, employee_rows: list[dict]) -> list[dict]:
    logger.info("Documents: authenticating with the Personio v2 API...")
    token = authenticate_v2(config.base_url, config.client_id, config.client_secret)
    owner_ids = [row["employeeID"] for row in employee_rows if row.get("employeeID")]
    docs = fetch_all_document_metadata(config.base_url, token, owner_ids)
    download_dir = None
    if config.documents_download_files:
        download_dir = os.path.join(config.output_dir, config.documents_subdir)
    return build_document_manifest(docs, config.base_url, token, download_dir)


def _print_summary(summary_rows: list[dict]) -> None:
    print("\nDepartment summary")
    print("-" * 52)
    print(f"{'department':<24}{'count':>8}{'avg base salary':>20}")
    for row in summary_rows:
        avg = row["average_base_salary"]
        avg_text = f"{avg:,.2f}" if isinstance(avg, (int, float)) else "-"
        print(f"{row['department']:<24}{row['employee_count']:>8}{avg_text:>20}")
    print("-" * 52)


def run(config_path: str, force_mock: bool | None = None, mock_count: int | None = None) -> int:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        logger.error("Configuration problem: %s", exc)
        return 1

    # --live / --mock override the config file.
    if force_mock is True:
        config.use_mock_data = True
        if mock_count is not None:
            config.mock_employee_count = mock_count
    elif force_mock is False:
        config.use_mock_data = False
        if not config.client_id or not config.client_secret:
            logger.error(
                "--live requires API credentials. Set PERSONIO_CLIENT_ID and "
                "PERSONIO_CLIENT_SECRET in .env (or client_id/client_secret in "
                "config.yaml)."
            )
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
        employee_path = write_employee_csv(
            config.output_dir, config.employee_file, CSV_COLUMNS, employee_rows
        )
        summary_path = write_summary_csv(
            config.output_dir, config.summary_file, SUMMARY_COLUMNS, summary_rows
        )
    except OSError as exc:
        logger.error("Could not write output: %s", exc)
        return 1

    output_files = [employee_path, summary_path]

    if config.documents_enabled:
        if config.use_mock_data:
            logger.info("Documents: skipped in mock mode (needs live v2 API access).")
        else:
            try:
                doc_rows = _export_documents(config, employee_rows)
                output_files.append(
                    write_documents_manifest(
                        config.output_dir,
                        config.documents_manifest_file,
                        DOCUMENT_MANIFEST_COLUMNS,
                        doc_rows,
                    )
                )
            except (DocumentAPIError, OSError) as exc:
                logger.warning("Documents: skipped (%s)", exc)

    try:
        deliver(output_files, config)
    except DeliveryError as exc:
        logger.error("Delivery failed: %s", exc)
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--live",
        action="store_true",
        help="Force live mode (call the Personio API), ignoring use_mock_data in the config.",
    )
    mode.add_argument(
        "--mock",
        nargs="?",
        const=-1,
        type=int,
        metavar="N",
        help="Force mock mode. Optionally give a number of synthetic employees "
        "to generate (e.g. --mock 2000). --mock 0 uses the small built-in sample.",
    )
    args = parser.parse_args()

    force_mock: bool | None = None
    mock_count: int | None = None
    if args.live:
        force_mock = False
    elif args.mock is not None:
        force_mock = True
        if args.mock >= 0:
            mock_count = args.mock

    _setup_logging()
    sys.exit(run(args.config, force_mock=force_mock, mock_count=mock_count))


if __name__ == "__main__":
    main()
