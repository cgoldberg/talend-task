# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


import logging
import time

import pytest
import requests

from talend_task.talend_client import (
    TALEND_API_VERSION,
    StaticTokenCredential,
    _TalendSession,
)


@pytest.fixture
def session():
    return _TalendSession(StaticTokenCredential("token123"))


def test_session_logs_success(monkeypatch, caplog, session):
    url = "https://api.example.com/foo"
    status_code = 200

    def fake_send(_self, _request, **_kwargs):
        resp = requests.Response()
        resp.status_code = 200
        resp.url = _request.url
        resp._content = b"OK"
        return resp

    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    with caplog.at_level(logging.DEBUG):
        session.request("GET", url)
    assert f"HTTP GET {url} -> {status_code} (45.0ms)" in caplog.text
    assert "Request Headers:" in caplog.text
    assert "Response Headers:" in caplog.text
    assert "Response Body:\nOK" in caplog.text


def test_session_logs_request_error(monkeypatch, caplog, session):
    url = "https://api.example.com/notfound"
    status_code = 404

    def fake_send(_self, _request, **_kwargs):
        resp = requests.Response()
        resp.status_code = status_code
        resp.url = _request.url
        resp._content = b"Not Found"
        return resp

    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    with caplog.at_level(logging.DEBUG):
        resp = session.request("GET", url)
        with pytest.raises(
            requests.HTTPError,
            match=f"{status_code} Client Error: None for url: {url}",
        ):
            resp.raise_for_status()
    assert f"HTTP GET {url} -> {status_code} (45.0ms)" in caplog.text
    assert "Request Headers:" in caplog.text
    assert "Response Headers:" in caplog.text
    assert "Response Body:\nNot Found" in caplog.text


def test_session_logs_request_exception(monkeypatch, caplog, session):
    url = "https://api.example.com/foo"
    error_msg = "boom"

    def fake_send(_self, _request, **_kwargs):
        raise requests.RequestException(error_msg)

    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    with (
        caplog.at_level(logging.DEBUG),
        pytest.raises(requests.RequestException, match=error_msg),
    ):
        session.request("GET", url)
    assert f"HTTP FAIL GET {url} -> None (45.0ms)" in caplog.text
    assert "Request Headers:" in caplog.text
    assert f"Error: RequestException('{error_msg}')" in caplog.text


def test_session_auth(monkeypatch, session):
    url = "https://api.example.com/foo"
    captured = {}

    def fake_send(_self, _request, **_kwargs):
        captured["headers"] = _request.headers
        resp = requests.Response()
        resp.url = _request.url
        return resp

    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    session.request("GET", url)
    assert captured["headers"]["Authorization"] == "Bearer token123"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["headers"]["talend-version"] == TALEND_API_VERSION
