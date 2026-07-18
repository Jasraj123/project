"""Configuration loading from config.yaml, with secrets from a .env file.

Credential precedence: environment variable > .env > config.yaml > default.
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
    """Load KEY=VALUE lines from a .env file into os.environ (existing vars win)."""
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
    delivery_type: str = "local"
    sftp_host: str = ""
    sftp_port: int = 22
    sftp_username: str = ""
    sftp_remote_dir: str = "."
    sftp_private_key_path: str = ""
    sftp_password: str = ""
    documents_enabled: bool = False
    documents_download_files: bool = False
    documents_manifest_file: str = "documents_manifest.csv"
    documents_subdir: str = "documents"


def load_config(path: str) -> Config:
    if not os.path.exists(path):
        raise ConfigError(
            f"Config file not found at '{path}'. "
            "Copy config.example.yaml to config.yaml and fill it in."
        )

    load_dotenv()

    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    personio = raw.get("personio", {})
    export = raw.get("export", {})
    use_mock_data = bool(raw.get("use_mock_data", False))

    base_url = (
        os.environ.get("PERSONIO_BASE_URL")
        or personio.get("base_url")
        or "https://api.personio.de"
    )
    client_id = os.environ.get("PERSONIO_CLIENT_ID") or personio.get("client_id", "")
    client_secret = os.environ.get("PERSONIO_CLIENT_SECRET") or personio.get("client_secret", "")

    try:
        mock_employee_count = int(raw.get("mock_employee_count", 0) or 0)
    except (TypeError, ValueError):
        raise ConfigError(
            "mock_employee_count must be a whole number (e.g. 2000), or 0 to use "
            "the small built-in sample."
        ) from None
    if mock_employee_count < 0:
        raise ConfigError("mock_employee_count cannot be negative.")

    delivery = raw.get("delivery", {})
    sftp = delivery.get("sftp", {})
    documents = raw.get("documents", {})

    config = Config(
        base_url=base_url.rstrip("/"),
        client_id=client_id,
        client_secret=client_secret,
        output_dir=export.get("output_dir", "./output"),
        employee_file=export.get("employee_file", "personio_employee_export.csv"),
        summary_file=export.get("summary_file", "department_summary.csv"),
        use_mock_data=use_mock_data,
        mock_employee_count=mock_employee_count,
        delivery_type=str(delivery.get("type", "local")),
        sftp_host=sftp.get("host", ""),
        sftp_port=int(sftp.get("port", 22) or 22),
        sftp_username=sftp.get("username", ""),
        sftp_remote_dir=sftp.get("remote_dir", "."),
        sftp_private_key_path=sftp.get("private_key_path", ""),
        sftp_password=os.environ.get("PERSONIO_SFTP_PASSWORD", ""),
        documents_enabled=bool(documents.get("enabled", False)),
        documents_download_files=bool(documents.get("download_files", False)),
        documents_manifest_file=documents.get("manifest_file", "documents_manifest.csv"),
        documents_subdir=documents.get("subdir", "documents"),
    )

    if not config.use_mock_data and (not config.client_id or not config.client_secret):
        raise ConfigError(
            "API token missing: client_id and client_secret are required "
            "when use_mock_data is false. Add PERSONIO_CLIENT_ID and "
            "PERSONIO_CLIENT_SECRET to your .env file (or client_id/"
            "client_secret to config.yaml), or set use_mock_data: true to "
            "run with sample data."
        )

    return config
