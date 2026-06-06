# Copyright (c) 2026 Corey Goldberg
# License: MIT


"""Tests for talend_task TalendClient."""

from unittest.mock import Mock

from talend_task.talend_client import TalendClient


def test_client_sets_headers():
    client = TalendClient(
        "https://api.example.com/",
        "abc123",
    )

    assert client.session.headers["Authorization"] == "Bearer abc123"
    assert client.session.headers["Content-Type"] == "application/json"


def test_get_calls_session_get():
    client = TalendClient(
        "https://api.example.com/",
        "token",
    )

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


def test_post_calls_session_post():
    client = TalendClient(
        "https://api.example.com/",
        "token",
    )

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


def test_get_jobs_returns_name_and_executable_pairs():
    client = TalendClient(
        "https://api.example.com/",
        "token",
    )

    client._get = Mock(
        return_value={
            "items": [
                {
                    "name": "job1",
                    "executable": "abc",
                },
                {
                    "name": "job2",
                    "executable": "def",
                },
            ]
        }
    )

    assert client.get_jobs() == [
        ("job1", "abc"),
        ("job2", "def"),
    ]


def test_get_execution_status():
    client = TalendClient(
        "https://api.example.com/",
        "token",
    )

    client._get = Mock(return_value={"status": "executing"})

    assert client.get_execution_status("exec-123") == "executing"

    client._get.assert_called_once_with("/executions/exec-123")


def test_run_job_returns_execution_id():
    client = TalendClient(
        "https://api.example.com/",
        "token",
    )

    client._post = Mock(return_value={"executionId": "exec-123"})

    result = client.run_job("job-456")

    assert result == "exec-123"

    client._post.assert_called_once_with(
        "/executions",
        {"executable": "job-456"},
    )


def test_run_without_wait_returns_unknown_status():
    client = TalendClient(
        "https://api.example.com/",
        "token",
    )

    client.run_job = Mock(return_value="exec-123")

    result = client.run("job-456")

    assert result == "unknown"


def test_run_waits_until_completion(monkeypatch):
    client = TalendClient(
        "https://api.example.com/",
        "token",
    )

    client.run_job = Mock(return_value="exec-123")

    statuses = iter(
        [
            "dispatching",
            "executing",
            "executing",
            "completed",
        ]
    )

    client.get_execution_status = Mock(side_effect=lambda _: next(statuses))

    sleep = Mock()
    monkeypatch.setattr(
        "talend_task.talend_client.time.sleep",
        sleep,
    )

    result = client.run(
        "job-456",
        wait=True,
        poll_interval=1,
    )

    assert result == "completed"
    assert sleep.call_count == 3
