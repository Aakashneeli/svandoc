"""FastAPI application bootstrap for svanDoc backend."""

from __future__ import annotations

from fastapi import FastAPI, Request

from svandoc_backend import __version__
from svandoc_backend.envelope import success_envelope

app = FastAPI(
    title="svanDoc Backend API",
    version=__version__,
)


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    return success_envelope(
        request,
        data={
            "service": "svandoc-backend",
            "status": "ok",
        },
    )


@app.get("/ready")
async def ready(request: Request) -> dict[str, object]:
    return success_envelope(
        request,
        data={
            "service": "svandoc-backend",
            "status": "ready",
            "checks": {
                "api": "ok",
            },
        },
    )
