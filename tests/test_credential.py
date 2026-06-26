# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


import time
from unittest.mock import Mock

import pytest

from talend_task.talend_client import (
    OAuthClientCredential,
    StaticTokenCredential,
)


@pytest.fixture
def oauth_credential():
    return OAuthClientCredential(
        api_url="https://api.example.com",
        client_id="client-id",
        client_secret="client-secret",
    )


@pytest.fixture
def oauth_credential_with_scope():
    return OAuthClientCredential(
        api_url="https://api.example.com",
        client_id="client-id",
        client_secret="client-secret",
        scope="read write",
    )


def test_static_token_adds_bearer_authorization_header():
    credential = StaticTokenCredential("my-token")

    headers = {}
    result = credential.apply(headers)

    assert result is headers
    assert headers["Authorization"] == "Bearer my-token"


@pytest.mark.parametrize(
    ("api_url", "expected"),
    [
        pytest.param(
            "https://api.example.com",
            "https://api.example.com/security/oauth/token",
            id="no_trailing_slash",
        ),
        pytest.param(
            "https://api.example.com/",
            "https://api.example.com/security/oauth/token",
            id="trailing_slash",
        ),
    ],
)
def test_oauth_client_token_url_is_normalized(api_url, expected):
    credential = OAuthClientCredential(
        api_url=api_url,
        client_id="client",
        client_secret="secret",
    )
    assert credential.token_url == expected


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        pytest.param(
            None,
            {"grant_type": "client_credentials"},
            id="no_scope",
        ),
        pytest.param(
            "read write",
            {"grant_type": "client_credentials", "scope": "read write"},
            id="with_scope",
        ),
    ],
)
def test_oauth_client_build_payload(scope, expected):
    credential = OAuthClientCredential(
        api_url="https://api.example.com",
        client_id="client",
        client_secret="secret",
        scope=scope,
    )
    assert credential._build_payload() == expected


@pytest.mark.parametrize(
    ("access_token", "expires_offset", "expected"),
    [
        pytest.param("token", 3600, False, id="valid"),
        pytest.param("token", -10, True, id="expired"),
        pytest.param(None, 0, True, id="no_token"),
    ],
)
def test_oauth_client_needs_refresh(
    access_token,
    expires_offset,
    expected,
    oauth_credential,
):
    oauth_credential._access_token = access_token
    oauth_credential._expires_at = time.time() + expires_offset
    assert oauth_credential._needs_refresh() is expected


@pytest.mark.parametrize(
    ("expires_offset", "expected"),
    [
        pytest.param(10, False, id="not_expired"),
        pytest.param(-10, True, id="expired"),
    ],
)
def test_oauth_client_is_expired(expires_offset, expected, oauth_credential):
    oauth_credential._expires_at = time.time() + expires_offset
    assert oauth_credential._is_expired() is expected


@pytest.mark.parametrize(
    ("now", "expires_in", "buffer_seconds", "expected"),
    [
        pytest.param(1000, 120, 30, 1090, id="explicit_expires_in"),
        pytest.param(1000, None, 30, 4570, id="default_expires_in"),
        pytest.param(1000, 100, 45, 1055, id="custom_buffer"),
    ],
)
def test_oauth_client_compute_expiry(
    monkeypatch,
    oauth_credential,
    now,
    expires_in,
    buffer_seconds,
    expected,
):
    monkeypatch.setattr("talend_task.talend_client.time.time", lambda: now)
    oauth_credential._buffer_seconds = buffer_seconds
    token_response = {}
    if expires_in is not None:
        token_response["expires_in"] = expires_in
    assert oauth_credential._compute_expiry(token_response) == expected


@pytest.mark.parametrize(
    (
        "access_token",
        "expires_offset",
        "refresh_effect",
        "expected_token",
        "refresh_called",
    ),
    [
        pytest.param(
            None,
            0,
            lambda cred: setattr(cred, "_access_token", "fresh-token"),
            "fresh-token",
            True,
            id="no_token_triggers_refresh",
        ),
        pytest.param(
            "old-token",
            -1,
            lambda cred: setattr(cred, "_access_token", "refreshed-token"),
            "refreshed-token",
            True,
            id="expired_token_triggers_refresh",
        ),
        pytest.param(
            "valid-token",
            3600,
            lambda cred: None,
            "valid-token",
            False,
            id="valid_token_no_refresh",
        ),
    ],
)
def test_oauth_client_apply(
    monkeypatch,
    oauth_credential,
    access_token,
    expires_offset,
    refresh_effect,
    expected_token,
    refresh_called,
):
    oauth_credential._access_token = access_token
    oauth_credential._expires_at = time.time() + expires_offset
    called = False

    def fake_refresh():
        nonlocal called
        called = True
        refresh_effect(oauth_credential)

    monkeypatch.setattr(oauth_credential, "_refresh", fake_refresh)
    headers = {}
    oauth_credential.apply(headers)
    assert headers["Authorization"] == f"Bearer {expected_token}"
    assert called is refresh_called


def test_oauth_client_refresh_fetches_token_and_updates_state(
    monkeypatch,
    oauth_credential,
):
    response = Mock()
    response.json.return_value = {
        "access_token": "new-token",
        "expires_in": 3600,
    }
    monkeypatch.setattr(
        "talend_task.talend_client.requests.post",
        lambda *args, **kwargs: response,
    )
    monkeypatch.setattr(oauth_credential, "_compute_expiry", lambda _: 9999)
    oauth_credential._refresh()
    response.raise_for_status.assert_called_once()
    assert oauth_credential._access_token == "new-token"
    assert oauth_credential._expires_at == 9999


def test_oauth_client_refresh_sends_scope_when_configured(
    monkeypatch,
    oauth_credential_with_scope,
):
    response = Mock()
    response.json.return_value = {"access_token": "t", "expires_in": 3600}
    captured = {}

    def fake_post(*args, **kwargs):
        captured["data"] = kwargs.get("data")
        return response

    monkeypatch.setattr("talend_task.talend_client.requests.post", fake_post)
    monkeypatch.setattr(oauth_credential_with_scope, "_compute_expiry", lambda _: 9999)
    oauth_credential_with_scope._refresh()
    assert captured["data"] == {
        "grant_type": "client_credentials",
        "scope": "read write",
    }


def test_oauth_client_refresh_propagates_http_errors(monkeypatch, oauth_credential):
    response = Mock()
    response.raise_for_status.side_effect = RuntimeError("boom")
    monkeypatch.setattr(
        "talend_task.talend_client.requests.post",
        lambda *args, **kwargs: response,
    )
    with pytest.raises(RuntimeError, match="boom"):
        oauth_credential._refresh()


def test_oauth_client_close_closes_session(oauth_credential):
    class FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    fake_session = FakeSession()
    oauth_credential._session = fake_session
    oauth_credential.close()
    assert fake_session.closed is True
