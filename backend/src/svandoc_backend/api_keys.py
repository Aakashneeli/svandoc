"""Public API key authentication helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from svandoc_backend.envelope import error_envelope


@dataclass(frozen=True)
class ApiKeyPrincipal:
    key_id: str
    scopes: set[str]


def _load_key_rows() -> list[dict[str, object]]:
    raw = os.getenv("PUBLIC_API_KEYS_JSON", "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    rows: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def resolve_api_key_principal(api_key: str) -> ApiKeyPrincipal | None:
    for row in _load_key_rows():
        key_value = str(row.get("key", "")).strip()
        if not key_value or key_value != api_key:
            continue
        scopes_value = row.get("scopes")
        scopes: set[str] = set()
        if isinstance(scopes_value, list):
            for scope in scopes_value:
                scope_text = str(scope).strip()
                if scope_text:
                    scopes.add(scope_text)
        key_id = str(row.get("id", "")).strip() or "public-client"
        return ApiKeyPrincipal(key_id=key_id, scopes=scopes)
    return None


def require_api_key_scope(request: Request, required_scope: str) -> tuple[ApiKeyPrincipal | None, JSONResponse | None]:
    supplied = request.headers.get("x-api-key", "").strip()
    if not supplied:
        return None, JSONResponse(
            status_code=401,
            content=error_envelope(
                request,
                code="UNAUTHORIZED",
                message="Missing API key.",
                details={"header": "x-api-key"},
                retryable=False,
            ),
        )

    principal = resolve_api_key_principal(supplied)
    if principal is None:
        return None, JSONResponse(
            status_code=401,
            content=error_envelope(
                request,
                code="UNAUTHORIZED",
                message="Invalid API key.",
                details=None,
                retryable=False,
            ),
        )

    if "*" in principal.scopes or required_scope in principal.scopes:
        return principal, None

    return None, JSONResponse(
        status_code=403,
        content=error_envelope(
            request,
            code="FORBIDDEN",
            message="API key does not include required scope.",
            details={"required_scope": required_scope, "granted_scopes": sorted(principal.scopes)},
            retryable=False,
        ),
    )
