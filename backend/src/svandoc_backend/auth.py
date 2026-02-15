"""Role-based authorization helpers for API endpoints."""

from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse

from svandoc_backend.envelope import error_envelope

VALID_ROLES = {"admin", "editor", "viewer"}
DEFAULT_ROLE = "admin"


def resolve_request_role(request: Request) -> str:
    role = request.headers.get("x-user-role", "").strip().lower()
    if role:
        return role
    return os.getenv("AUTH_DEFAULT_ROLE", DEFAULT_ROLE).strip().lower() or DEFAULT_ROLE


def require_roles(request: Request, allowed_roles: set[str]) -> JSONResponse | None:
    role = resolve_request_role(request)
    if role not in VALID_ROLES:
        return JSONResponse(
            status_code=403,
            content=error_envelope(
                request,
                code="FORBIDDEN",
                message="Invalid role for this action.",
                details={"role": role, "valid_roles": sorted(VALID_ROLES)},
                retryable=False,
            ),
        )
    if role not in allowed_roles:
        return JSONResponse(
            status_code=403,
            content=error_envelope(
                request,
                code="FORBIDDEN",
                message="Role is not authorized for this action.",
                details={"role": role, "required_roles": sorted(allowed_roles)},
                retryable=False,
            ),
        )
    return None
