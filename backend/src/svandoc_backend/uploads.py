"""Upload helpers for file persistence and metadata extraction."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

DEFAULT_LOCAL_STORAGE_PATH = "./data/storage"
DEFAULT_MAX_UPLOAD_MB = 25
DEFAULT_MAX_UPLOAD_PAGES = 20

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic"}
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/heic",
}

PDF_PAGE_PATTERN = re.compile(rb"/Type\s*/Page\b")


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def estimate_page_count(content: bytes, mime_type: str) -> int:
    if mime_type == "application/pdf":
        page_count = len(PDF_PAGE_PATTERN.findall(content))
        return page_count if page_count > 0 else 1
    return 1


def local_storage_root() -> Path:
    configured_path = os.getenv("LOCAL_STORAGE_PATH", DEFAULT_LOCAL_STORAGE_PATH).strip()
    if not configured_path:
        configured_path = DEFAULT_LOCAL_STORAGE_PATH
    return Path(configured_path)


def safe_filename(filename: str | None) -> str:
    cleaned = Path(filename or "upload.bin").name.strip()
    return cleaned or "upload.bin"


def normalized_mime_type(raw_mime_type: str | None) -> str:
    return (raw_mime_type or "application/octet-stream").strip().lower()


def max_upload_bytes() -> int:
    raw = os.getenv("MAX_UPLOAD_MB", str(DEFAULT_MAX_UPLOAD_MB)).strip()
    try:
        mb = int(raw)
        if mb <= 0:
            return DEFAULT_MAX_UPLOAD_MB * 1024 * 1024
        return mb * 1024 * 1024
    except ValueError:
        return DEFAULT_MAX_UPLOAD_MB * 1024 * 1024


def max_upload_pages() -> int:
    raw = os.getenv("MAX_UPLOAD_PAGES", str(DEFAULT_MAX_UPLOAD_PAGES)).strip()
    try:
        pages = int(raw)
        if pages <= 0:
            return DEFAULT_MAX_UPLOAD_PAGES
        return pages
    except ValueError:
        return DEFAULT_MAX_UPLOAD_PAGES


def validate_upload(filename: str | None, mime_type: str | None, content: bytes) -> tuple[list[str], int]:
    issues: list[str] = []
    safe_name = safe_filename(filename)
    mime = normalized_mime_type(mime_type)
    extension = Path(safe_name).suffix.lower()

    if mime not in SUPPORTED_MIME_TYPES and extension not in SUPPORTED_EXTENSIONS:
        issues.append("Unsupported file type. Allowed: PDF, PNG, JPG/JPEG, TIFF, HEIC.")

    upload_size = len(content)
    max_size = max_upload_bytes()
    if upload_size > max_size:
        max_mb = max_size // (1024 * 1024)
        issues.append(f"File size exceeds limit of {max_mb} MB.")

    page_count = estimate_page_count(content, mime)
    max_pages = max_upload_pages()
    if page_count > max_pages:
        issues.append(f"Page count exceeds limit of {max_pages} pages.")

    return issues, page_count


def persist_local_file(document_id: str, filename: str | None, content: bytes) -> str:
    root = local_storage_root()
    root.mkdir(parents=True, exist_ok=True)

    target = root / document_id / safe_filename(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return str(target.resolve())
