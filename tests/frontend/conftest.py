"""Shared pytest fixtures for the frontend test suite.

Makes the ``frontend`` package importable (it lives at ``frontend/`` and is not on ``pythonpath``
by default) and provides a fake HTTP transport so API-client tests run without a real backend,
network, or credentials.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

# Make the ``frontend`` package importable: the repository root (the parent of ``frontend/``)
# must be on ``sys.path`` so that ``import frontend`` resolves to the package.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    """Ensure the frontend package is importable before test modules are collected."""
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))


class FakeTransport(httpx.BaseTransport):
    """A minimal ``httpx`` transport driven by a handler function.

    The handler receives the outgoing :class:`httpx.Request` and returns an :class:`httpx.Response`.
    This lets tests assert on the exact request (method, path, headers, body) and control the
    response, without any real network access.
    """

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._handler = handler
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def make_transport(handler: Callable[[httpx.Request], httpx.Response]) -> FakeTransport:
    """Build a :class:`FakeTransport` around ``handler``."""
    return FakeTransport(handler)


def json_response(status_code: int, payload: Any) -> httpx.Response:
    """Build a JSON :class:`httpx.Response`."""
    import json

    return httpx.Response(status_code, content=json.dumps(payload).encode("utf-8"))


@pytest.fixture
def base_url() -> str:
    return "http://testserver"
