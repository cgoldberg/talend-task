# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


import logging
import time
from unittest.mock import MagicMock, Mock, call

import pytest
import requests

from talend_task import TalendClient
from talend_task.talend_client import (
    HTTP_TIMEOUT,
    POLL_INTERVAL,
    TALEND_API_VERSION,
    _AuthSession,
    _LoggedSession,
)


class FakeResponse:
    def __init__(
        self,
        status_code=200,
        url="https://api.example.com",
        text="OK",
        headers=None,
    ):
        self.status_code = status_code
        self.url = url
        self.text = text
        self.headers = headers or {}


@pytest.fixture
def client():
    return TalendClient("https://api.example.com", "token123")


def test_client_sets_headers(client):
    assert client._session.headers["Authorization"] == "Bearer token123"
    assert client._session.headers["Content-Type"] == "application/json"
    assert client._session.headers["talend-version"] == TALEND_API_VERSION


def test_context_manager_closes_session(client):
    fake_session = MagicMock()
    client._session = fake_session
    with client as c:
        assert c is client
    fake_session.close.assert_called_once()


def test_context_manager_closes_on_exception(client):
    fake_session = MagicMock()
    client._session = fake_session
    with pytest.raises(ValueError, match="boom"):
        with client:
            raise ValueError("boom")
    fake_session.close.assert_called_once()


def test_get_calls_session_get(client):
    response_payload = {"foo": "bar"}
    response = Mock()
    response.json.return_value = response_payload
    client._session.get = Mock(return_value=response)
    result = client._get("/test")
    assert result == response_payload
    client._session.get.assert_called_once_with(
        "https://api.example.com/processing/test",
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status.assert_called_once()


def test_post_calls_session_post(client):
    response_payload = {"foo": "bar"}
    response = Mock()
    response.json.return_value = response_payload
    client._session.post = Mock(return_value=response)
    payload = {"hello": "world"}
    result = client._post("/test", payload)
    assert result == response_payload
    client._session.post.assert_called_once_with(
        "https://api.example.com/processing/test",
        json=payload,
        timeout=HTTP_TIMEOUT,
    )


def test_close_closes_session_and_clears_cache(client):
    fake_session = MagicMock()
    client._session = fake_session
    client._jobs_cache = [{"name": "job1", "executable": "abc"}]
    client.close()
    fake_session.close.assert_called_once()
    assert client._jobs_cache is None


def test_close_is_idempotent(client):
    fake_session = MagicMock()
    client._session = fake_session
    client.close()
    client.close()
    assert fake_session.close.call_count == 2
    assert client._jobs_cache is None


def test_jobs_are_cached(monkeypatch, client):
    jobs = [
        {"name": "job1", "executable": "abc"},
        {"name": "job2", "executable": "xyz"},
    ]
    calls = []

    def fake_get(path):
        calls.append(path)
        return {"items": jobs}

    monkeypatch.setattr(client, "_get", fake_get)
    assert client._jobs_cache is None
    result1 = client._jobs()
    assert result1 == jobs
    assert client._jobs_cache == jobs
    result2 = client._jobs()
    assert result2 == jobs
    assert client._jobs_cache == jobs
    assert len(calls) == 1
    assert calls == ["/executables/tasks"]


def test_get_jobs_returns_name_and_executable_pairs(client):
    jobs = [
        {"name": "job1", "executable": "abc"},
        {"name": "job2", "executable": "xyz"},
    ]
    expected = [("job1", "abc"), ("job2", "xyz")]
    client._jobs = Mock(return_value=jobs)
    assert client.get_jobs() == expected


def test_get_job_id(client):
    jobs = [
        {"name": "job1", "executable": "abc"},
        {"name": "job2", "executable": "xyz"},
    ]
    client._jobs = Mock(return_value=jobs)
    assert client.get_job_id("job2") == "xyz"


def test_get_job_id_raises_for_unknown_job(client):
    jobs = [
        {"name": "job1", "executable": "abc"},
        {"name": "job2", "executable": "xyz"},
    ]
    client._jobs = Mock(return_value=jobs)
    with pytest.raises(ValueError, match="Unknown job: job3"):
        client.get_job_id("job3")


def test_get_execution_status(client):
    client._get = Mock(return_value={"status": "executing"})
    assert client.get_execution_status("exec-123") == "executing"
    client._get.assert_called_once_with("/executions/exec-123")


def test_get_executions_sorts_and_limits(client):
    fake_result = {
        "items": [
            {
                "taskVersion": "1.1",
                "runtime": {"type": "REMOTE_ENGINE"},
                "executionStatus": "EXECUTION_SUCCESS",
                "startTimestamp": "2026-06-09T10:00:00.000Z",
                "finishTimestamp": "2026-06-09T10:10:00.000Z",
                "userId": "user1",
            },
            {
                "taskVersion": "1.1",
                "runtime": {"type": "CLOUD"},
                "executionStatus": "EXECUTION_FAILED",
                "startTimestamp": "2026-06-09T12:00:00.000Z",
                "finishTimestamp": "2026-06-09T12:05:00.000Z",
                "userId": "user2",
            },
            {
                "taskVersion": "1.1",
                "runtime": {"type": "REMOTE_ENGINE"},
                "executionStatus": "EXECUTION_RUNNING",
                "startTimestamp": "2026-06-09T11:00:00.000Z",
                "finishTimestamp": None,
                "userId": "user3",
            },
        ]
    }
    client._get = Mock(return_value=fake_result)
    job_id = "abc123"
    executions = client.get_executions(job_id, limit=2)
    client._get.assert_called_once_with(f"/executables/tasks/{job_id}/executions")
    assert isinstance(executions, list)
    assert len(executions) == 2
    assert [r["start_timestamp"] for r in executions] == [
        "2026-06-09T12:00:00.000Z",
        "2026-06-09T11:00:00.000Z",
    ]


def test_run_job_returns_execution_id(client):
    job_id = "abc123"
    client._post = Mock(return_value={"executionId": "exec-123"})
    execution_id = client.run_job(job_id)
    assert execution_id == "exec-123"
    client._post.assert_called_once_with("/executions", {"executable": job_id})


def test_run_polls_until_completion_when_waiting(monkeypatch, client):
    client.run_job = Mock(return_value="exec-123")
    statuses = ("dispatching", "executing", "execution_successful")
    client.get_execution_status = Mock(side_effect=statuses)
    sleep = Mock()
    monkeypatch.setattr("talend_task.talend_client.time.sleep", sleep)
    status = client.run("job1", wait=True, poll_interval=1)
    assert status == "execution_successful"
    assert sleep.call_args_list == [call(1), call(1)]


def test_run_uses_default_poll_interval(monkeypatch, client):
    client.run_job = Mock(return_value="exec-123")
    statuses = ("dispatching", "executing", "execution_successful")
    client.get_execution_status = Mock(side_effect=statuses)
    sleep = Mock()
    monkeypatch.setattr("talend_task.talend_client.time.sleep", sleep)
    status = client.run("job1", wait=True)
    assert status == "execution_successful"
    assert sleep.call_args_list == [call(POLL_INTERVAL), call(POLL_INTERVAL)]


def test_run_does_not_poll_and_returns_unknown(client):
    client.run_job = Mock(return_value="exec-123")
    client.get_execution_status = Mock()
    status1 = client.run("job1")
    status2 = client.run("job2", wait=False)
    expected_status = "unknown"
    assert status1 == expected_status
    assert status2 == expected_status
    client.get_execution_status.assert_not_called()


def test_run_times_out(monkeypatch, client):
    job_name = "job1"
    timeout = 5
    client.run_job = Mock(return_value="exec-123")
    client.get_execution_status = Mock(return_value="executing")
    monkeypatch.setattr(
        "talend_task.talend_client.time.monotonic",
        Mock(side_effect=[0.0, 10.0]),
    )
    monkeypatch.setattr("talend_task.talend_client.time.sleep", lambda _: None)
    with pytest.raises(
        TimeoutError,
        match=f"Job {job_name} did not complete within {timeout} seconds",
    ):
        client.run(job_name, wait=True, timeout=timeout)


def test_logged_session_success(monkeypatch, caplog):
    def fake_send(*args, **kwargs):
        return FakeResponse()

    session = _LoggedSession()
    times = iter([100.0, 100.123])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    with caplog.at_level(logging.DEBUG):
        resp = session.request("GET", "https://api.example.com")
    assert isinstance(resp, FakeResponse)
    assert "HTTP GET" in caplog.text
    assert "200" in caplog.text
    assert "Headers:" in caplog.text
    assert "Body:" in caplog.text


def test_logged_session_request_exception(monkeypatch, caplog):
    def fake_send(*args, **kwargs):
        raise requests.RequestException("boom")

    session = _LoggedSession()
    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(requests.Session, "send", fake_send)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(requests.RequestException):
            session.request("GET", "https://api.example.com")
    assert "HTTP FAIL GET" in caplog.text
    assert "boom" in caplog.text


def test_auth_session():
    access_token = "token123"
    session = _AuthSession(access_token)
    assert isinstance(session, requests.Session)
    assert isinstance(session, _LoggedSession)
    assert session.headers["Authorization"] == f"Bearer {access_token}"
    assert session.headers["Content-Type"] == "application/json"
    assert session.headers["talend-version"] == TALEND_API_VERSION
