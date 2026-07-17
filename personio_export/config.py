"""Load and validate configuration from a YAML file.

Keeping configuration in a file (never hard-coded) means a customer can set up
the tool without touching the code, and secrets stay out of the source.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import yaml


class ConfigError(Exception):
    """Raised when the configuration file is missing or incomplete."""


@dataclass
class Config:
    base_url: str
    client_id: str
    client_secret: str
    output_dir: str
    employee_file: str
    summary_file: str
    use_mock_data: bool


def load_config(path: str) -> Config:
    """Read the YAML config file and return a validated Config object."""
    if not os.path.exists(path):
        raise ConfigError(
            f"Config file not found at '{path}'. "
            "Copy config.example.yaml to config.yaml and fill it in."
        )

    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    personio = raw.get("personio", {})
    export = raw.get("export", {})
    use_mock_data = bool(raw.get("use_mock_data", False))

    config = Config(
        base_url=personio.get("base_url", "https://api.personio.de").rstrip("/"),
        client_id=personio.get("client_id", ""),
        client_secret=personio.get("client_secret", ""),
        output_dir=export.get("output_dir", "./output"),
        employee_file=export.get("employee_file", "personio_employee_export.csv"),
        summary_file=export.get("summary_file", "department_summary.csv"),
        use_mock_data=use_mock_data,
    )

    # Only require credentials when we actually intend to call the API.
    if not config.use_mock_data:
        if not config.client_id or not config.client_secret:
            raise ConfigError(
                "API token missing: client_id and client_secret are required "
                "when use_mock_data is false. Add them to config.yaml or set "
                "use_mock_data: true to run with sample data."
            )

    return config
