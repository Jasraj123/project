"""Write the transformed rows to CSV files on the local disk."""

from __future__ import annotations

import csv
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _write_csv(path: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
    directory = os.path.dirname(path) or "."
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as exc:
        raise OSError(f"Cannot create output folder '{directory}': {exc}") from exc

    try:
        with open(path, "w", newline="", encoding="utf-8") as handle:
            # extrasaction="ignore" drops non-schema keys like "_currency".
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    except OSError as exc:
        raise OSError(f"Cannot write CSV file '{path}': {exc}") from exc


def write_employee_csv(
    output_dir: str, filename: str, columns: list[str], rows: list[dict[str, Any]]
) -> str:
    path = os.path.join(output_dir, filename)
    _write_csv(path, columns, rows)
    logger.info("CSV generated successfully: %s (%d rows)", path, len(rows))
    return path


def write_summary_csv(
    output_dir: str, filename: str, columns: list[str], rows: list[dict[str, Any]]
) -> str:
    path = os.path.join(output_dir, filename)
    _write_csv(path, columns, rows)
    logger.info("Department summary written: %s (%d rows)", path, len(rows))
    return path


def write_documents_manifest(
    output_dir: str, filename: str, columns: list[str], rows: list[dict[str, Any]]
) -> str:
    path = os.path.join(output_dir, filename)
    _write_csv(path, columns, rows)
    logger.info("Document manifest written: %s (%d rows)", path, len(rows))
    return path
