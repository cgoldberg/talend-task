# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


from unittest.mock import Mock, call

import pytest

from talend_task.talend_client import TalendClient


@pytest.fixture
def client():
    return TalendClient("https://api.example.com/", "abc123")


def test_client_sets_headers(client):
    assert client.session.headers["Authorization"] == "Bearer abc123"
    assert client.session.headers["Content-Type"] == "application/json"


def test_get_calls_session_get(client):
    response = Mock()
    response.json.return_value = {"hello": "world"}
    client.session.get = Mock(return_value=response)
    result = client._get("/foo")
    assert result == {"hello": "world"}
    client.session.get.assert_called_once_with(
        "https://api.example.com/processing/foo",
        timeout=30,
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
        timeout=30,
    )


def test_get_jobs_returns_name_and_executable_pairs(client):
    response_payload = {
        "items": [
            {"name": "job1", "executable": "abc"},
            {"name": "job2", "executable": "xyz"},
        ]
    }
    expected = [("job1", "abc"), ("job2", "xyz")]
    client._get = Mock(return_value=response_payload)
    assert client.get_jobs() == expected


def test_get_execution_status(client):
    client._get = Mock(return_value={"status": "executing"})
    assert client.get_execution_status("exec-123") == "executing"
    client._get.assert_called_once_with("/executions/exec-123")


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


def test_run_does_not_poll_and_returns_unknown(client):
    client.run_job = Mock(return_value="exec-123")
    client.get_execution_status = Mock()
    status1 = client.run("job-123")
    status2 = client.run("job-456", wait=False)
    expected_status = "unknown"
    assert status1 == expected_status
    assert status2 == expected_status
    client.get_execution_status.assert_not_called()


def test_run_uses_default_polling_interval(monkeypatch, client):
    client.run_job = Mock(return_value="exec-123")
    statuses = ("dispatching", "executing", "execution_successful")
    client.get_execution_status = Mock(side_effect=statuses)
    sleep = Mock()
    monkeypatch.setattr("talend_task.talend_client.time.sleep", sleep)
    status = client.run("job-456", wait=True, timeout=None, poll_interval=None)
    assert status == "execution_successful"
    assert sleep.call_args_list == [call(5), call(5)]


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
