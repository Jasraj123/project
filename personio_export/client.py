"""Personio API client: authenticate, then fetch employees.

Uses the v1 employee endpoint, with pagination for large companies and
automatic retries on transient errors.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Personio caps the v1 employees endpoint at 100 records per page (422 above it).
PAGE_SIZE = 100

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2  # doubles each attempt: 2s, 4s, 8s
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

MAX_PAGES = 1000


class PersonioAPIError(Exception):
    """Raised when the Personio API returns an error or cannot be reached."""


class PersonioClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout
        self._token: str | None = None

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_error = ""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.request(method, url, timeout=self._timeout, **kwargs)
            except requests.RequestException as exc:
                last_error = f"network error: {exc}"
            else:
                if response.status_code not in RETRYABLE_STATUS:
                    return response
                last_error = f"HTTP {response.status_code}"

            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Personio request failed (%s). Retry %d/%d in %ds...",
                    last_error,
                    attempt,
                    MAX_RETRIES - 1,
                    wait,
                )
                time.sleep(wait)

        raise PersonioAPIError(
            f"Personio request failed after {MAX_RETRIES} attempts ({last_error})."
        )

    def authenticate(self) -> None:
        if not self._client_id or not self._client_secret:
            raise PersonioAPIError("API token missing: client_id/client_secret not set.")

        logger.info("Authenticating with Personio...")
        response = self._request_with_retry(
            "POST",
            f"{self.base_url}/v1/auth",
            json={"client_id": self._client_id, "client_secret": self._client_secret},
        )

        if response.status_code == 401:
            raise PersonioAPIError(
                "Authentication failed (401): check your client_id and client_secret."
            )
        if not response.ok:
            raise PersonioAPIError(
                f"Authentication failed ({response.status_code}): {response.text[:200]}"
            )

        token = response.json().get("data", {}).get("token")
        if not token:
            raise PersonioAPIError("Authentication succeeded but no token was returned.")

        self._token = token
        logger.info("Authentication successful.")

    def fetch_employees(self) -> list[dict[str, Any]]:
        if not self._token:
            raise PersonioAPIError("Not authenticated. Call authenticate() first.")

        logger.info("Fetching employees from Personio...")
        headers = {"Authorization": f"Bearer {self._token}"}
        employees: list[dict[str, Any]] = []
        offset = 0

        for _ in range(MAX_PAGES):
            response = self._request_with_retry(
                "GET",
                f"{self.base_url}/v1/company/employees",
                headers=headers,
                params={"limit": PAGE_SIZE, "offset": offset},
            )

            if response.status_code == 403:
                raise PersonioAPIError(
                    "Access denied (403): the API credentials are missing permissions or "
                    "the required employee attributes are not whitelisted."
                )
            if response.status_code == 422:
                raise PersonioAPIError(
                    "Personio rejected the request parameters (422). The v1 employees "
                    f"endpoint allows at most 100 records per page (PAGE_SIZE={PAGE_SIZE})."
                )
            if not response.ok:
                raise PersonioAPIError(
                    f"Failed to fetch employees ({response.status_code}): {response.text[:200]}"
                )

            body = response.json()
            batch = body.get("data", [])
            employees.extend(batch)

            total_pages = (body.get("metadata") or {}).get("total_pages")
            if total_pages is not None:
                if offset // PAGE_SIZE >= total_pages - 1:
                    break
            elif len(batch) < PAGE_SIZE:
                break

            if not batch:
                break

            offset += PAGE_SIZE
            logger.info("Fetched %d so far, requesting more...", len(employees))

        logger.info("Fetched %d employees", len(employees))
        return employees
