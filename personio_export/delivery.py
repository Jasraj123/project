"""Deliver the exported files to their destination.

The brief's "Load" step: files are always written locally first, then optionally
delivered elsewhere. Today "local" (no-op) and "sftp" are supported; adding a new
target (email, cloud bucket) means adding one function here.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from personio_export.config import Config

logger = logging.getLogger(__name__)


class DeliveryError(Exception):
    """Raised when files cannot be delivered to the configured destination."""


def deliver(file_paths: list[str], config: Config) -> None:
    destination = (config.delivery_type or "local").lower()

    if destination == "local":
        logger.info("Delivery: local only - %d file(s) left in the output folder.", len(file_paths))
        return
    if destination == "sftp":
        _deliver_sftp(file_paths, config)
        return
    raise DeliveryError(f"Unknown delivery type '{config.delivery_type}' (use 'local' or 'sftp').")


def _deliver_sftp(file_paths: list[str], config: Config) -> None:
    try:
        import paramiko
    except ImportError as exc:
        raise DeliveryError(
            "SFTP delivery needs the 'paramiko' package. Install it with: pip install paramiko"
        ) from exc

    if not config.sftp_host or not config.sftp_username:
        raise DeliveryError("SFTP delivery requires sftp.host and sftp.username in the config.")
    if not config.sftp_private_key_path and not config.sftp_password:
        raise DeliveryError(
            "SFTP delivery needs a credential: set PERSONIO_SFTP_PASSWORD in .env, "
            "or sftp.private_key_path in the config."
        )

    logger.info(
        "Delivery: uploading %d file(s) to sftp://%s@%s:%d%s ...",
        len(file_paths),
        config.sftp_username,
        config.sftp_host,
        config.sftp_port,
        config.sftp_remote_dir,
    )

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs = {
            "hostname": config.sftp_host,
            "port": config.sftp_port,
            "username": config.sftp_username,
            "timeout": 30,
        }
        if config.sftp_private_key_path:
            connect_kwargs["key_filename"] = config.sftp_private_key_path
        else:
            connect_kwargs["password"] = config.sftp_password

        ssh.connect(**connect_kwargs)
        sftp = ssh.open_sftp()
        try:
            for local_path in file_paths:
                remote_path = os.path.join(config.sftp_remote_dir, os.path.basename(local_path))
                sftp.put(local_path, remote_path)
                logger.info("Uploaded %s -> %s", os.path.basename(local_path), remote_path)
        finally:
            sftp.close()
    except DeliveryError:
        raise
    except Exception as exc:  # paramiko raises a variety of low-level errors
        raise DeliveryError(f"SFTP delivery failed: {exc}") from exc
    finally:
        ssh.close()

    logger.info("Delivery: SFTP upload complete.")
