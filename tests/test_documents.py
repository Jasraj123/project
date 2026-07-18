"""Tests for the v2 document export (auth, cursor pagination, manifest), mocked."""

import tempfile
import unittest
from unittest.mock import MagicMock, patch

from personio_export.documents import (
    DocumentAPIError,
    authenticate_v2,
    build_document_manifest,
    fetch_all_document_metadata,
    fetch_document_metadata,
)


def _resp(status, json_body=None, text=""):
    resp = MagicMock()
    resp.status_code = status
    resp.ok = 200 <= status < 300
    resp.json.return_value = json_body or {}
    resp.text = text
    return resp


class AuthV2Tests(unittest.TestCase):
    def test_returns_access_token(self):
        with patch(
            "personio_export.documents.requests.post",
            return_value=_resp(200, {"access_token": "papi-x"}),
        ):
            self.assertEqual(authenticate_v2("https://api", "id", "sec"), "papi-x")

    def test_invalid_scope_gives_clear_error(self):
        with patch(
            "personio_export.documents.requests.post",
            return_value=_resp(400, text='{"error":"invalid_scope"}'),
        ):
            with self.assertRaises(DocumentAPIError) as ctx:
                authenticate_v2("https://api", "id", "sec")
        self.assertIn("documents:read", str(ctx.exception))


class FetchMetadataTests(unittest.TestCase):
    def test_paginates_with_cursor(self):
        page1 = _resp(200, {"_data": [{"id": 1}], "_meta": {"cursor": {"next": "abc"}}})
        page2 = _resp(200, {"_data": [{"id": 2}], "_meta": {"cursor": {"next": None}}})
        with patch("personio_export.documents.requests.get", side_effect=[page1, page2]) as get:
            docs = fetch_document_metadata("https://api", "tok", owner_id="99")
        self.assertEqual([d["id"] for d in docs], [1, 2])
        self.assertEqual(get.call_count, 2)
        # owner_id must be passed to the API.
        self.assertEqual(get.call_args_list[0].kwargs["params"]["owner_id"], "99")

    def test_403_raises(self):
        with patch(
            "personio_export.documents.requests.get", return_value=_resp(403, text="forbidden")
        ):
            with self.assertRaises(DocumentAPIError):
                fetch_document_metadata("https://api", "tok", owner_id="1")

    def test_fetch_all_aggregates_and_tags_owner(self):
        per_owner = {
            "1": _resp(200, {"_data": [{"id": 10}], "_meta": {}}),
            "2": _resp(200, {"_data": [{"id": 20}], "_meta": {}}),
        }
        with patch(
            "personio_export.documents.requests.get",
            side_effect=lambda url, headers, params, timeout: per_owner[params["owner_id"]],
        ):
            docs = fetch_all_document_metadata("https://api", "tok", ["1", "2"])
        self.assertEqual({d["id"] for d in docs}, {10, 20})
        self.assertEqual({d["owner"]["id"] for d in docs}, {"1", "2"})


class ManifestTests(unittest.TestCase):
    def test_manifest_without_download(self):
        docs = [
            {
                "id": 10,
                "name": "Contract.pdf",
                "category": {"id": 5},
                "owner": {"id": 99},
                "document_type": "application/pdf",
                "size": 100,
                "created_at": "2024-01-01",
            }
        ]
        rows = build_document_manifest(docs)
        self.assertEqual(rows[0]["document_id"], 10)
        self.assertEqual(rows[0]["employee_id"], 99)
        self.assertEqual(rows[0]["downloaded_file"], "")

    def test_manifest_downloads_when_requested(self):
        docs = [{"id": 10, "name": "Contract.pdf"}]
        with tempfile.TemporaryDirectory() as tmp:
            with patch("personio_export.documents.download_document") as download:
                rows = build_document_manifest(docs, "https://api", "tok", tmp)
            download.assert_called_once()
        self.assertTrue(rows[0]["downloaded_file"])


if __name__ == "__main__":
    unittest.main()
