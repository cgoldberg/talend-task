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
    status_code = 200
    url = "https://api.example.com/foo"

    def fake_send(self, request, **kwargs):
        resp = requests.Response()
        resp.status_code = 200
        resp.url = request.url
        resp._content = b"OK"
        return resp

    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    with caplog.at_level(logging.DEBUG):
        session.request("GET", url)
    assert f"HTTP GET {url} -> {status_code} (45.0ms)" in caplog.text
    assert "Headers:" in caplog.text
    assert "Body: OK" in caplog.text


def test_session_logs_request_error(monkeypatch, caplog, session):
    status_code = 404
    url = "https://api.example.com/notfound"

    def fake_send(self, request, **kwargs):
        resp = requests.Response()
        resp.status_code = status_code
        resp.url = request.url
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
    assert "Headers:" in caplog.text
    assert "Body: Not Found" in caplog.text


def test_session_logs_request_exception(monkeypatch, caplog, session):
    error = "boom"

    def fake_send(self, request, **kwargs):
        raise requests.RequestException(error)

    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    url = "https://api.example.com/foo"
    with pytest.raises(requests.RequestException, match=error):
        session.request("GET", url)
    msg = (
        f"HTTP FAIL GET {url} -> None (45.0ms) "
        f"| error=RequestException('{error}') | body=None"
    )
    assert msg in caplog.text


def test_session_auth(monkeypatch, session):
    url = "https://api.example.com/foo"
    access_token = "token123"
    captured = {}

    def fake_send(self, request, **kwargs):
        captured["headers"] = request.headers
        resp = requests.Response()
        resp.url = request.url
        return resp

    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    session.request("GET", url)
    assert captured["headers"]["Authorization"] == f"Bearer {access_token}"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["headers"]["talend-version"] == TALEND_API_VERSION
