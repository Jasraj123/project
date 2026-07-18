"""Tests for the delivery layer (local no-op and SFTP upload, with paramiko mocked)."""

import sys
import unittest
from unittest.mock import MagicMock, patch

from personio_export.config import Config
from personio_export.delivery import DeliveryError, deliver


def _config(**overrides):
    base = dict(
        base_url="https://api.personio.de",
        client_id="",
        client_secret="",
        output_dir="./output",
        employee_file="e.csv",
        summary_file="s.csv",
        use_mock_data=True,
        mock_employee_count=0,
    )
    base.update(overrides)
    return Config(**base)


class LocalDeliveryTests(unittest.TestCase):
    def test_local_is_a_noop(self):
        # Should not raise and needs no third-party packages.
        deliver(["output/a.csv"], _config(delivery_type="local"))

    def test_unknown_type_raises(self):
        with self.assertRaises(DeliveryError):
            deliver([], _config(delivery_type="ftp"))


class SftpDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.paramiko = MagicMock()
        patcher = patch.dict(sys.modules, {"paramiko": self.paramiko})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_missing_host_raises(self):
        with self.assertRaises(DeliveryError):
            deliver(["f.csv"], _config(delivery_type="sftp", sftp_username="u", sftp_password="p"))

    def test_missing_credentials_raises(self):
        with self.assertRaises(DeliveryError):
            deliver(["f.csv"], _config(delivery_type="sftp", sftp_host="h", sftp_username="u"))

    def test_uploads_each_file(self):
        cfg = _config(
            delivery_type="sftp",
            sftp_host="h",
            sftp_username="u",
            sftp_password="p",
            sftp_remote_dir="/upload",
        )
        ssh = self.paramiko.SSHClient.return_value
        sftp = ssh.open_sftp.return_value

        deliver(["/tmp/a.csv", "/tmp/b.csv"], cfg)

        ssh.connect.assert_called_once()
        self.assertEqual(sftp.put.call_count, 2)
        sftp.put.assert_any_call("/tmp/a.csv", "/upload/a.csv")


if __name__ == "__main__":
    unittest.main()
