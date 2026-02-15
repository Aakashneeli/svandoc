"""In-memory API rate limiting and abuse guardrails."""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from fastapi import Request


@dataclass
class RateLimitDecision:
    allowed: bool
    code: str | None = None
    reason: str | None = None
    retry_after_seconds: int | None = None


class InMemoryRateLimiter:
    def __init__(self, now_fn: Callable[[], float] | None = None) -> None:
        self._now = now_fn or time.time
        self._lock = threading.Lock()
        self._events: dict[str, deque[float]] = {}
        self._blocked_until: dict[str, float] = {}

    def _read_int_env(self, name: str, default: int) -> int:
        raw = os.getenv(name, str(default)).strip()
        try:
            parsed = int(raw)
        except ValueError:
            return default
        return parsed if parsed > 0 else default

    def _enabled(self) -> bool:
        raw = os.getenv("RATE_LIMIT_ENABLED", "1").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def _window_seconds(self) -> int:
        return self._read_int_env("RATE_LIMIT_WINDOW_SECONDS", 60)

    def _max_requests(self, request_path: str) -> int:
        if request_path.startswith("/api/documents/upload"):
            return self._read_int_env("RATE_LIMIT_UPLOAD_MAX_REQUESTS", 30)
        return self._read_int_env("RATE_LIMIT_MAX_REQUESTS", 300)

    def _block_seconds(self) -> int:
        return self._read_int_env("RATE_LIMIT_BLOCK_SECONDS", 300)

    def evaluate(self, key: str, request_path: str) -> RateLimitDecision:
        if not self._enabled():
            return RateLimitDecision(allowed=True)

        now = self._now()
        window = self._window_seconds()
        max_requests = self._max_requests(request_path)
        abuse_trigger = max_requests + 2

        with self._lock:
            blocked_until = self._blocked_until.get(key, 0.0)
            if blocked_until > now:
                return RateLimitDecision(
                    allowed=False,
                    code="ABUSE_BLOCKED",
                    reason="abuse_blocked",
                    retry_after_seconds=max(1, int(blocked_until - now)),
                )

            events = self._events.setdefault(key, deque())
            while events and (now - events[0]) > window:
                events.popleft()

            events.append(now)
            current = len(events)
            if current <= max_requests:
                return RateLimitDecision(allowed=True)

            if current >= abuse_trigger:
                block_seconds = self._block_seconds()
                self._blocked_until[key] = now + block_seconds
                return RateLimitDecision(
                    allowed=False,
                    code="ABUSE_BLOCKED",
                    reason="abuse_blocked",
                    retry_after_seconds=block_seconds,
                )

            retry_after = max(1, int(window - (now - events[0])))
            return RateLimitDecision(
                allowed=False,
                code="RATE_LIMITED",
                reason="rate_limit_exceeded",
                retry_after_seconds=retry_after,
            )

    def reset_for_tests(self) -> None:
        with self._lock:
            self._events.clear()
            self._blocked_until.clear()


def rate_limit_subject(request: Request) -> str:
    user_id = request.headers.get("x-user-id", "").strip()
    if user_id:
        return f"user:{user_id}"

    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return f"ip:{client_ip}"

    if request.client and request.client.host:
        return f"ip:{request.client.host}"
    return "anonymous"


def should_rate_limit_path(path: str) -> bool:
    return path.startswith("/api/")


rate_limiter = InMemoryRateLimiter()
