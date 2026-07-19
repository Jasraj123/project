"""Tests for configuration loading: .env support and env-var precedence."""

import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from personio_export.config import ConfigError, load_config, load_dotenv

_ENV_KEYS = ["PERSONIO_CLIENT_ID", "PERSONIO_CLIENT_SECRET", "PERSONIO_BASE_URL"]


class _CleanEnv(unittest.TestCase):
    """Save/restore the PERSONIO_* env vars between tests."""

    def setUp(self):
        self._saved = {key: os.environ.get(key) for key in _ENV_KEYS}
        for key in _ENV_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _write_config(dir_path, personio, use_mock_data):
    path = os.path.join(dir_path, "config.yaml")
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "personio": personio,
                "export": {"output_dir": os.path.join(dir_path, "output")},
                "use_mock_data": use_mock_data,
            },
            handle,
        )
    return path


class ConfigEnvPrecedenceTests(_CleanEnv):
    def setUp(self):
        super().setUp()
        # Ignore any real project-root .env so these tests control the environment.
        patcher = patch("personio_export.config.load_dotenv", lambda *a, **k: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_env_var_overrides_yaml_credentials(self):
        os.environ["PERSONIO_CLIENT_ID"] = "env-id"
        os.environ["PERSONIO_CLIENT_SECRET"] = "env-secret"
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_config(
                tmp,
                {"client_id": "yaml-id", "client_secret": "yaml-secret"},
                use_mock_data=False,
            )
            config = load_config(path)
        self.assertEqual(config.client_id, "env-id")
        self.assertEqual(config.client_secret, "env-secret")

    def test_yaml_credentials_used_when_env_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_config(
                tmp,
                {"client_id": "yaml-id", "client_secret": "yaml-secret"},
                use_mock_data=False,
            )
            config = load_config(path)
        self.assertEqual(config.client_id, "yaml-id")

    def test_live_mode_without_credentials_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_config(tmp, {"client_id": "", "client_secret": ""}, use_mock_data=False)
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_mock_mode_does_not_require_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_config(tmp, {"client_id": "", "client_secret": ""}, use_mock_data=True)
            config = load_config(path)
        self.assertTrue(config.use_mock_data)

    def test_non_numeric_sftp_port_raises_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.yaml")
            with open(path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    {
                        "personio": {},
                        "export": {"output_dir": os.path.join(tmp, "output")},
                        "use_mock_data": True,
                        "delivery": {"type": "sftp", "sftp": {"port": "notanumber"}},
                    },
                    handle,
                )
            with self.assertRaises(ConfigError):
                load_config(path)


class LoadDotenvTests(_CleanEnv):
    def test_loads_values_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write('# a comment\n\nPERSONIO_CLIENT_ID="file-id"\n')
                handle.write("export PERSONIO_CLIENT_SECRET=file-secret\n")
            load_dotenv(env_path)
        self.assertEqual(os.environ.get("PERSONIO_CLIENT_ID"), "file-id")
        self.assertEqual(os.environ.get("PERSONIO_CLIENT_SECRET"), "file-secret")

    def test_does_not_overwrite_existing_env(self):
        os.environ["PERSONIO_CLIENT_ID"] = "already-set"
        with tempfile.TemporaryDirectory() as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write('PERSONIO_CLIENT_ID="from-file"\n')
            load_dotenv(env_path)
        self.assertEqual(os.environ.get("PERSONIO_CLIENT_ID"), "already-set")

    def test_missing_file_is_a_noop(self):
        # Should not raise for a path that does not exist.
        load_dotenv(os.path.join(tempfile.gettempdir(), "does-not-exist-12345.env"))


if __name__ == "__main__":
    unittest.main()
