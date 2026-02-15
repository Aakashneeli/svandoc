"""Cloud connector upload helpers for export artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


class CloudConnectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class CloudUploadResult:
    provider: str
    remote_id: str
    storage_uri: str


def upload_to_google_drive(
    *,
    access_token: str,
    filename: str,
    content: bytes,
    mime_type: str,
    folder_id: str | None = None,
    timeout_seconds: float = 15.0,
) -> CloudUploadResult:
    metadata: dict[str, Any] = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    multipart_boundary = "svandoc-google-drive-boundary"
    metadata_json = json.dumps(metadata, separators=(",", ":"), ensure_ascii=True)
    body = (
        f"--{multipart_boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{metadata_json}\r\n"
        f"--{multipart_boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{multipart_boundary}--\r\n".encode("utf-8")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": f"multipart/related; boundary={multipart_boundary}",
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id",
                headers=headers,
                content=body,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise CloudConnectorError(f"google_drive_upload_failed:{exc}") from exc

    remote_id = str(payload.get("id", "")).strip()
    if not remote_id:
        raise CloudConnectorError("google_drive_upload_failed:missing_file_id")

    return CloudUploadResult(
        provider="gdrive",
        remote_id=remote_id,
        storage_uri=f"gdrive://{remote_id}",
    )


def upload_to_onedrive(
    *,
    access_token: str,
    filename: str,
    content: bytes,
    folder_path: str = "svandoc-exports",
    timeout_seconds: float = 15.0,
) -> CloudUploadResult:
    safe_folder = folder_path.strip("/").strip() or "svandoc-exports"
    safe_filename = filename.strip() or "export.json"
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{safe_folder}/{safe_filename}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.put(url, headers=headers, content=content)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise CloudConnectorError(f"onedrive_upload_failed:{exc}") from exc

    remote_id = str(payload.get("id", "")).strip()
    if not remote_id:
        raise CloudConnectorError("onedrive_upload_failed:missing_file_id")

    return CloudUploadResult(
        provider="onedrive",
        remote_id=remote_id,
        storage_uri=f"onedrive://{remote_id}",
    )


def upload_to_dropbox(
    *,
    access_token: str,
    filename: str,
    content: bytes,
    folder_path: str = "/svandoc-exports",
    timeout_seconds: float = 15.0,
) -> CloudUploadResult:
    normalized_folder = folder_path.strip()
    if not normalized_folder.startswith("/"):
        normalized_folder = f"/{normalized_folder}"
    normalized_folder = normalized_folder.rstrip("/") or "/svandoc-exports"
    safe_filename = filename.strip() or "export.json"
    dropbox_path = f"{normalized_folder}/{safe_filename}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": json.dumps(
            {
                "path": dropbox_path,
                "mode": "add",
                "autorename": True,
                "mute": False,
                "strict_conflict": False,
            },
            separators=(",", ":"),
            ensure_ascii=True,
        ),
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                "https://content.dropboxapi.com/2/files/upload",
                headers=headers,
                content=content,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise CloudConnectorError(f"dropbox_upload_failed:{exc}") from exc

    remote_id = str(payload.get("id", "")).strip()
    if not remote_id:
        raise CloudConnectorError("dropbox_upload_failed:missing_file_id")

    return CloudUploadResult(
        provider="dropbox",
        remote_id=remote_id,
        storage_uri=f"dropbox://{remote_id}",
    )

