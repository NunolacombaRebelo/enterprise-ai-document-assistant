"""Tests for the frontend configuration helpers (``frontend/config.py``)."""

from __future__ import annotations

import importlib

from frontend import config


def test_default_api_base_url(monkeypatch) -> None:
    monkeypatch.delenv("API_BASE_URL", raising=False)
    importlib.reload(config)
    assert config.get_api_base_url() == "http://localhost:8000"


def test_api_base_url_from_env(monkeypatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "http://api:8000")
    importlib.reload(config)
    assert config.get_api_base_url() == "http://api:8000"


def test_api_base_url_trailing_slash_stripped(monkeypatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8000/")
    importlib.reload(config)
    assert config.get_api_base_url() == "http://localhost:8000"


def test_api_base_url_blank_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "   ")
    importlib.reload(config)
    assert config.get_api_base_url() == "http://localhost:8000"


def test_is_pdf_filename() -> None:
    assert config.is_pdf_filename("report.pdf")
    assert config.is_pdf_filename("REPORT.PDF")
    assert not config.is_pdf_filename("report.txt")
    assert not config.is_pdf_filename("report.pdf.exe")
