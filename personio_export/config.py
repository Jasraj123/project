"""Load and validate configuration from a YAML file (and, for secrets, a .env).

Keeping configuration in a file (never hard-coded) means a customer can set up
the tool without touching the code, and secrets stay out of the source.

Precedence for the API credentials and base URL:
    environment variable  >  .env file  >  config.yaml  >  built-in default

This lets non-secret settings live in a readable, committable ``config.yaml``
while the secret credentials live only in a ``.env`` file (which is gitignored),
following common security practice.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when the configuration file is missing or incomplete."""


def load_dotenv(path: str = ".env") -> None:
    """Load simple ``KEY=VALUE`` lines from a .env file into the environment.

    Existing environment variables are never overwritten (a real shell variable
    wins over the file). Blank lines and ``#`` comments are ignored, and inline
    surrounding quotes are stripped. Kept dependency-free on purpose.
    """
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, _, value = stripped.partition("=")
                key = key.strip()
                # Allow an optional "export " prefix, as in shell env files.
                if key.startswith("export "):
                    key = key[len("export ") :].strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
    except OSError as exc:
        logger.warning("Could not read .env file '%s': %s", path, exc)


@dataclass
class Config:
    base_url: str
    client_id: str
    client_secret: str
    output_dir: str
    employee_file: str
    summary_file: str
    use_mock_data: bool
    mock_employee_count: int


def load_config(path: str) -> Config:
    """Read the YAML config file and return a validated Config object."""
    if not os.path.exists(path):
        raise ConfigError(
            f"Config file not found at '{path}'. "
            "Copy config.example.yaml to config.yaml and fill it in."
        )

    # Load .env first so its values are available as environment variables below.
    load_dotenv()

    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    personio = raw.get("personio", {})
    export = raw.get("export", {})
    use_mock_data = bool(raw.get("use_mock_data", False))

    # Credentials and base URL may come from the environment (.env), which takes
    # precedence over config.yaml so secrets can be kept out of the YAML file.
    base_url = (
        os.environ.get("PERSONIO_BASE_URL")
        or personio.get("base_url")
        or "https://api.personio.de"
    )
    client_id = os.environ.get("PERSONIO_CLIENT_ID") or personio.get("client_id", "")
    client_secret = os.environ.get("PERSONIO_CLIENT_SECRET") or personio.get("client_secret", "")

    # When >0 and running in mock mode, generate this many synthetic employees
    # instead of using the small built-in sample (handy for a realistic demo).
    try:
        mock_employee_count = int(raw.get("mock_employee_count", 0) or 0)
    except (TypeError, ValueError):
        raise ConfigError(
            "mock_employee_count must be a whole number (e.g. 2000), or 0 to use "
            "the small built-in sample."
        ) from None
    if mock_employee_count < 0:
        raise ConfigError("mock_employee_count cannot be negative.")

    config = Config(
        base_url=base_url.rstrip("/"),
        client_id=client_id,
        client_secret=client_secret,
        output_dir=export.get("output_dir", "./output"),
        employee_file=export.get("employee_file", "personio_employee_export.csv"),
        summary_file=export.get("summary_file", "department_summary.csv"),
        use_mock_data=use_mock_data,
        mock_employee_count=mock_employee_count,
    )

    # Only require credentials when we actually intend to call the API.
    if not config.use_mock_data:
        if not config.client_id or not config.client_secret:
            raise ConfigError(
                "API token missing: client_id and client_secret are required "
                "when use_mock_data is false. Add PERSONIO_CLIENT_ID and "
                "PERSONIO_CLIENT_SECRET to your .env file (or client_id/"
                "client_secret to config.yaml), or set use_mock_data: true to "
                "run with sample data."
            )

    return config
