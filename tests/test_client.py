"""Tests for the API client: authentication, pagination and error handling.

These cover the parts most likely to break against a real (large) tenant, so
they use a fake `requests.request` instead of hitting the network.
"""

import unittest
from unittest.mock import Mock, patch

from personio_export.client import PAGE_SIZE, PersonioAPIError, PersonioClient


def _auth_response(token="tok", status=200):
    resp = Mock()
    resp.status_code = status
    resp.ok = 200 <= status < 300
    resp.json.return_value = {"data": {"token": token}}
    resp.text = ""
    return resp


def _page_response(count, total_pages=None, status=200):
    resp = Mock()
    resp.status_code = status
    resp.ok = 200 <= status < 300
    body = {"data": [{"attributes": {"id": {"value": i}}} for i in range(count)]}
    if total_pages is not None:
        body["metadata"] = {"total_pages": total_pages}
    resp.json.return_value = body
    resp.text = "error body"
    return resp


class AuthenticateTests(unittest.TestCase):
    def test_token_is_stored_on_success(self):
        with patch("personio_export.client.requests.request", return_value=_auth_response("abc")):
            client = PersonioClient("https://api.personio.de", "id", "secret")
            client.authenticate()
            self.assertEqual(client._token, "abc")

    def test_401_raises_clear_error(self):
        with patch(
            "personio_export.client.requests.request", return_value=_auth_response(status=401)
        ):
            client = PersonioClient("https://api.personio.de", "id", "secret")
            with self.assertRaises(PersonioAPIError):
                client.authenticate()

    def test_missing_credentials_raises_before_calling_api(self):
        client = PersonioClient("https://api.personio.de", "", "")
        with self.assertRaises(PersonioAPIError):
            client.authenticate()


class FetchEmployeesTests(unittest.TestCase):
    def _authed_client(self):
        client = PersonioClient("https://api.personio.de", "id", "secret")
        client._token = "tok"
        return client

    def test_paginates_using_metadata(self):
        pages = [
            _page_response(PAGE_SIZE, total_pages=2),
            _page_response(30, total_pages=2),
        ]
        with patch("personio_export.client.requests.request", side_effect=pages) as mock_req:
            employees = self._authed_client().fetch_employees()
        self.assertEqual(len(employees), PAGE_SIZE + 30)
        self.assertEqual(mock_req.call_count, 2)

    def test_stops_on_short_page_without_metadata(self):
        pages = [_page_response(PAGE_SIZE), _page_response(10)]
        with patch("personio_export.client.requests.request", side_effect=pages) as mock_req:
            employees = self._authed_client().fetch_employees()
        self.assertEqual(len(employees), PAGE_SIZE + 10)
        self.assertEqual(mock_req.call_count, 2)

    def test_single_short_page_makes_one_call(self):
        with patch(
            "personio_export.client.requests.request", side_effect=[_page_response(5)]
        ) as mock_req:
            employees = self._authed_client().fetch_employees()
        self.assertEqual(len(employees), 5)
        self.assertEqual(mock_req.call_count, 1)

    def test_422_raises_clear_error(self):
        with patch(
            "personio_export.client.requests.request", side_effect=[_page_response(0, status=422)]
        ):
            with self.assertRaises(PersonioAPIError) as ctx:
                self._authed_client().fetch_employees()
        self.assertIn("422", str(ctx.exception))

    def test_403_raises_permission_error(self):
        with patch(
            "personio_export.client.requests.request", side_effect=[_page_response(0, status=403)]
        ):
            with self.assertRaises(PersonioAPIError) as ctx:
                self._authed_client().fetch_employees()
        self.assertIn("403", str(ctx.exception))

    def test_fetch_without_auth_raises(self):
        client = PersonioClient("https://api.personio.de", "id", "secret")
        with self.assertRaises(PersonioAPIError):
            client.fetch_employees()


if __name__ == "__main__":
    unittest.main()
