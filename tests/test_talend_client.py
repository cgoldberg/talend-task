# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


import logging
import time
from unittest.mock import Mock, call

import pytest
import requests

from talend_task.talend_client import (
    DEFAULT_POLL_INTERVAL,
    HTTP_TIMEOUT,
    TALEND_API_VERSION,
    LoggedSession,
    TalendClient,
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
    return TalendClient("https://api.example.com", "abc123")


def test_client_sets_headers(client):
    assert client.session.headers["Authorization"] == "Bearer abc123"
    assert client.session.headers["Content-Type"] == "application/json"
    assert client.session.headers["talend-version"] == TALEND_API_VERSION


def test_get_calls_session_get(client):
    response = Mock()
    response.json.return_value = {"hello": "world"}
    client.session.get = Mock(return_value=response)
    result = client._get("/foo")
    assert result == {"hello": "world"}
    client.session.get.assert_called_once_with(
        "https://api.example.com/processing/foo",
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status.assert_called_once()


def test_post_calls_session_post(client):
    response = Mock()
    response.json.return_value = {"id": 123}
    client.session.post = Mock(return_value=response)
    payload = {"a": 1}
    result = client._post("/foo", payload)
    assert result == {"id": 123}
    client.session.post.assert_called_once_with(
        "https://api.example.com/processing/foo",
        json=payload,
        timeout=HTTP_TIMEOUT,
    )


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
    client._post = Mock(return_value={"executionId": "exec-123"})
    execution_id = client.run_job("job-456")
    assert execution_id == "exec-123"
    client._post.assert_called_once_with("/executions", {"executable": "job-456"})


def test_run_polls_until_completion_when_waiting(monkeypatch, client):
    client.run_job = Mock(return_value="exec-123")
    statuses = ("dispatching", "executing", "execution_successful")
    client.get_execution_status = Mock(side_effect=statuses)
    sleep = Mock()
    monkeypatch.setattr("talend_task.talend_client.time.sleep", sleep)
    status = client.run("job-456", wait=True, poll_interval=1)
    assert status == "execution_successful"
    assert sleep.call_args_list == [call(1), call(1)]


def test_run_uses_default_poll_interval(monkeypatch, client):
    client.run_job = Mock(return_value="exec-123")
    statuses = ("dispatching", "executing", "execution_successful")
    client.get_execution_status = Mock(side_effect=statuses)
    sleep = Mock()
    monkeypatch.setattr("talend_task.talend_client.time.sleep", sleep)
    status = client.run("job-456", wait=True)
    assert status == "execution_successful"
    default = DEFAULT_POLL_INTERVAL
    assert sleep.call_args_list == [call(default), call(default)]


def test_run_does_not_poll_and_returns_unknown(client):
    client.run_job = Mock(return_value="exec-123")
    client.get_execution_status = Mock()
    status1 = client.run("job-123")
    status2 = client.run("job-456", wait=False)
    expected_status = "unknown"
    assert status1 == expected_status
    assert status2 == expected_status
    client.get_execution_status.assert_not_called()


def test_run_times_out(monkeypatch, client):
    job_name = "job-456"
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
    fake_resp = FakeResponse()
    session = LoggedSession()
    times = iter([100.0, 100.123])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))

    def fake_send(self, request, **kwargs):
        return fake_resp

    monkeypatch.setattr(requests.Session, "send", fake_send)
    with caplog.at_level(logging.DEBUG):
        resp = session.request("GET", "https://api.example.com")
    assert resp is fake_resp
    assert "HTTP GET" in caplog.text
    assert "200" in caplog.text
    assert "Headers:" in caplog.text
    assert "Body:" in caplog.text


def test_logged_session_request_exception(monkeypatch, caplog):
    session = LoggedSession()
    times = iter([100.0, 100.045])
    monkeypatch.setattr(time, "monotonic", lambda: next(times))

    def fake_send(self, request, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(requests.Session, "send", fake_send)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(requests.RequestException):
            session.request("GET", "https://api.example.com")
    assert "HTTP FAIL GET" in caplog.text
    assert "boom" in caplog.text
