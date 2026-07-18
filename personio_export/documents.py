"""Export HR documents via the Personio v2 Document Management API.

Document listing/download is only available on the v2 API, which uses OAuth 2.0
(client-credentials) auth and a ``documents:read`` scope - separate from the v1
employee export. This module authenticates against v2, lists document metadata
(writing a manifest CSV) and can optionally download the files.

If the credential lacks document access the API returns 403 / invalid_scope;
that is reported clearly and the rest of the export still succeeds.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

DOCUMENT_MANIFEST_COLUMNS = [
    "document_id",
    "name",
    "category_id",
    "employee_id",
    "document_type",
    "size",
    "created_at",
    "downloaded_file",
]


class DocumentAPIError(Exception):
    """Raised when the v2 document API cannot be reached or refuses access."""


def authenticate_v2(base_url: str, client_id: str, client_secret: str, timeout: int = 30) -> str:
    """Return a v2 OAuth 2.0 bearer token for the document-management scope."""
    response = requests.post(
        f"{base_url}/v2/auth/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "documents:read",
        },
        timeout=timeout,
    )
    if response.status_code == 400 and "invalid_scope" in response.text:
        raise DocumentAPIError(
            "This API credential does not have document access. Enable the "
            "'documents:read' scope on the credential in Personio to export documents."
        )
    if not response.ok:
        raise DocumentAPIError(
            f"v2 authentication failed ({response.status_code}): {response.text[:200]}"
        )
    token = response.json().get("access_token")
    if not token:
        raise DocumentAPIError("v2 authentication succeeded but no access token was returned.")
    return token


def fetch_document_metadata(
    base_url: str, token: str, owner_id: str, timeout: int = 30
) -> list[dict[str, Any]]:
    """List one employee's document metadata (the v2 endpoint requires owner_id)."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    documents: list[dict[str, Any]] = []
    params: dict[str, Any] = {"owner_id": owner_id}

    while True:
        response = requests.get(
            f"{base_url}/v2/document-management/documents",
            headers=headers,
            params=params,
            timeout=timeout,
        )
        if response.status_code == 403:
            raise DocumentAPIError(
                "Access denied (403) to document management. The credential is "
                "missing document permissions."
            )
        if not response.ok:
            raise DocumentAPIError(
                f"Failed to list documents ({response.status_code}): {response.text[:200]}"
            )

        body = response.json()
        documents.extend(body.get("_data", []))

        cursor = (body.get("_meta") or {}).get("cursor", {}).get("next")
        if not cursor:
            break
        params = {"owner_id": owner_id, "cursor": cursor}

    return documents


def fetch_all_document_metadata(
    base_url: str, token: str, owner_ids: list[str], timeout: int = 30
) -> list[dict[str, Any]]:
    """Aggregate document metadata across employees, tagging each with its owner."""
    all_documents: list[dict[str, Any]] = []
    for owner_id in owner_ids:
        for doc in fetch_document_metadata(base_url, token, owner_id, timeout):
            doc.setdefault("owner", {"id": owner_id})
            all_documents.append(doc)
    logger.info(
        "Found %d document(s) across %d employee(s)", len(all_documents), len(owner_ids)
    )
    return all_documents


def download_document(
    base_url: str, token: str, document_id: str, dest_path: str, timeout: int = 60
) -> None:
    """Download a single document's file to dest_path."""
    response = requests.get(
        f"{base_url}/v2/document-management/documents/{document_id}/download",
        headers={"Authorization": f"Bearer {token}", "Accept": "*/*"},
        timeout=timeout,
    )
    if response.status_code == 409:
        raise DocumentAPIError(f"Document {document_id} was flagged unsafe and cannot be downloaded.")
    if not response.ok:
        raise DocumentAPIError(
            f"Failed to download document {document_id} ({response.status_code})."
        )
    with open(dest_path, "wb") as handle:
        handle.write(response.content)


def _manifest_row(doc: dict[str, Any], downloaded_file: str = "") -> dict[str, Any]:
    return {
        "document_id": doc.get("id", ""),
        "name": doc.get("name", ""),
        "category_id": (doc.get("category") or {}).get("id", ""),
        "employee_id": (doc.get("owner") or {}).get("id", ""),
        "document_type": doc.get("document_type", ""),
        "size": doc.get("size", ""),
        "created_at": doc.get("created_at", ""),
        "downloaded_file": downloaded_file,
    }


def build_document_manifest(
    documents: list[dict[str, Any]],
    base_url: str = "",
    token: str = "",
    download_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Build manifest rows, optionally downloading each file into download_dir."""
    rows: list[dict[str, Any]] = []
    for doc in documents:
        downloaded_file = ""
        if download_dir and doc.get("id"):
            os.makedirs(download_dir, exist_ok=True)
            name = str(doc.get("name") or doc["id"]).replace("/", "_")
            dest = os.path.join(download_dir, f"{doc['id']}_{name}")
            try:
                download_document(base_url, token, str(doc["id"]), dest)
                downloaded_file = dest
            except DocumentAPIError as exc:
                logger.warning("Skipping document %s: %s", doc.get("id"), exc)
        rows.append(_manifest_row(doc, downloaded_file))
    return rows
