# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


import argparse
import sys
from unittest.mock import Mock

import pytest

from talend_task import cli


def _make_args(**kwargs):
    defaults = dict(
        job=None,
        timeout=None,
        poll_interval=None,
        wait=True,
        activity=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture(autouse=True)
def default_env(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN", "token")
    monkeypatch.setenv("API_URL", "https://api.example.com")


def test_require_env_returns_value(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN", "abc123")
    assert cli.require_env("ACCESS_TOKEN") == "abc123"


def test_require_env_missing():
    with pytest.raises(cli.ConfigError, match="Missing required environment variable"):
        cli.require_env("DOES_NOT_EXIST")


@pytest.mark.parametrize(
    ("seconds", "expected_time"),
    [
        pytest.param(0, "00:00:00", id="zero"),
        pytest.param(5, "00:00:05", id="seconds"),
        pytest.param(65, "00:01:05", id="minutes"),
        pytest.param(3661, "01:01:01", id="hours"),
    ],
)
def test_convert_time(seconds, expected_time):
    assert cli.convert_time(seconds) == expected_time


@pytest.mark.parametrize(
    ("start_timestamp", "end_timestamp", "expected"),
    [
        pytest.param(
            "2026-06-12T12:00:00.000Z",
            "2026-06-12T12:00:30.000Z",
            "00:00:30",
            id="30_secs",
        ),
        pytest.param(
            "2026-06-12T12:00:00.000Z",
            "2026-06-12T12:05:00.000Z",
            "00:05:00",
            id="5_mins",
        ),
        pytest.param(
            "2026-06-12T12:00:00.000Z",
            "2026-06-12T13:00:00.000Z",
            "01:00:00",
            id="1_hr",
        ),
    ],
)
def test_compute_duration(start_timestamp, end_timestamp, expected):
    assert cli.compute_duration(start_timestamp, end_timestamp) == expected


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        pytest.param(
            "2026-06-12T12:45:15.538Z",
            "06/12/2026 12:45 PM",
            id="timestamp1",
        ),
        pytest.param(
            "2026-01-01T00:00:00.000Z",
            "01/01/2026 12:00 AM",
            id="timestamp2",
        ),
        pytest.param(
            "2026-12-31T23:59:59.999Z",
            "12/31/2026 11:59 PM",
            id="timestamp3",
        ),
    ],
)
def test_format_iso_timestamp(timestamp, expected):
    assert cli.format_iso_timestamp(timestamp) == expected


@pytest.mark.parametrize(
    ("args_list", "expected"),
    [
        pytest.param(
            [],
            dict(
                wait=False,
                activity=False,
                timeout=None,
                poll_interval=None,
                job=None,
            ),
            id="defaults",
        ),
        pytest.param(
            ["--activity", "--job", "job1"],
            dict(
                wait=False,
                activity=True,
                timeout=None,
                poll_interval=None,
                job="job1",
            ),
            id="activity_no_wait",
        ),
        pytest.param(
            ["--wait", "--timeout", "30", "--poll-interval", "10", "--job", "job1"],
            dict(
                wait=True,
                activity=False,
                timeout=30,
                poll_interval=10,
                job="job1",
            ),
            id="timeout_poll_wait",
        ),
    ],
)
def test_parse_flags(args_list, expected):
    args = cli.parse_args(args_list)
    for key, value in expected.items():
        assert getattr(args, key) == value


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {},
            id="defaults",
        ),
        pytest.param(
            {"wait": True},
            id="wait_only",
        ),
        pytest.param(
            {"activity": True},
            id="activity_only",
        ),
        pytest.param(
            {"wait": True, "timeout": 1},
            id="wait_timeout",
        ),
        pytest.param(
            {"wait": True, "poll_interval": 1},
            id="wait_poll",
        ),
        pytest.param(
            {"wait": True, "timeout": 1, "poll_interval": 1},
            id="wait_timeout_poll",
        ),
    ],
)
def test_validate_args_valid(overrides):
    base = dict(
        job=None,
        timeout=None,
        poll_interval=None,
        wait=False,
        activity=False,
    )
    args = argparse.Namespace(**{**base, **overrides})
    result = cli.validate_args(args)
    assert result is None


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {"timeout": 0},
            id="timeout_zero",
        ),
        pytest.param(
            {"poll_interval": 0},
            id="poll_zero",
        ),
        pytest.param(
            {"timeout": -1},
            id="timeout_negative",
        ),
        pytest.param(
            {"poll_interval": -1},
            id="poll_negative",
        ),
        pytest.param(
            {"activity": True, "wait": True},
            id="activity_wait",
        ),
        pytest.param(
            {"activity": True, "timeout": 10},
            id="activity_timeout",
        ),
        pytest.param(
            {"activity": True, "poll_interval": 5},
            id="activity_poll",
        ),
        pytest.param(
            {"timeout": 10, "wait": False},
            id="timeout_without_wait",
        ),
        pytest.param(
            {"poll_interval": 5, "wait": False},
            id="poll_without_wait",
        ),
    ],
)
def test_validate_args_invalid(overrides):
    base = dict(
        job=None,
        timeout=None,
        poll_interval=None,
        wait=False,
        activity=False,
    )
    args = argparse.Namespace(**{**base, **overrides})
    result = cli.validate_args(args)
    assert "Error:" in result


def test_run_job_no_wait():
    client = Mock()
    client.run.return_value = "unknown"
    status, elapsed_time = cli.run_job(
        client,
        "job123",
        wait=False,
        timeout=None,
        poll_interval=None,
    )
    assert status == "unknown"
    assert elapsed_time is None
    client.run.assert_called_once_with("job123")


def test_run_job_wait(monkeypatch):
    client = Mock()
    client.run.return_value = "execution_successful"
    monkeypatch.setattr(
        "talend_task.cli.time.monotonic",
        Mock(side_effect=[100.0, 165.0]),
    )
    status, elapsed_time = cli.run_job(
        client,
        "job123",
        wait=True,
        timeout=None,
        poll_interval=5,
    )
    assert status == "execution_successful"
    assert elapsed_time == "00:01:05"


def test_run_cli_named_job_success():
    client = Mock()
    client.get_job_id.return_value = "id2"
    run_job_mock = Mock(return_value=("execution_successful", None))
    status = cli.run_cli(
        job_name="job2",
        wait=False,
        timeout=None,
        poll_interval=None,
        activity=False,
        client=client,
        jobs=None,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_successful"
    client.get_job_id.assert_called_once_with("job2")
    run_job_mock.assert_called_once_with(
        client,
        "id2",
        wait=False,
        timeout=None,
        poll_interval=None,
    )


def test_run_cli_named_job_fail():
    client = Mock()
    client.get_job_id.return_value = "id1"
    run_job_mock = Mock(return_value=("execution_failed", None))
    status = cli.run_cli(
        job_name="job1",
        wait=False,
        timeout=None,
        poll_interval=None,
        activity=False,
        client=client,
        jobs=None,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_failed"
    client.get_job_id.assert_called_once_with("job1")
    run_job_mock.assert_called_once_with(
        client,
        "id1",
        wait=False,
        timeout=None,
        poll_interval=None,
    )


def test_run_cli_invalid_job():
    client = Mock()
    unknown_job = "does_not_exist"
    client.get_job_id.side_effect = ValueError(f"Unknown job: {unknown_job}")
    with pytest.raises(ValueError, match=f"Unknown job: {unknown_job}"):
        cli.run_cli(
            job_name=unknown_job,
            wait=False,
            timeout=None,
            poll_interval=None,
            activity=False,
            client=client,
            jobs=None,
        )
    client.get_job_id.assert_called_once_with(unknown_job)


def test_run_cli_interactive_selection():
    def fake_input(prompt):
        return "2"

    client = Mock()
    jobs = [("job1", "id1"), ("job2", "id2")]
    run_job_mock = Mock(return_value=("execution_successful", None))
    status = cli.run_cli(
        job_name=None,
        wait=False,
        timeout=None,
        poll_interval=None,
        activity=False,
        client=client,
        jobs=jobs,
        input_fn=fake_input,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_successful"
    run_job_mock.assert_called_once_with(
        client,
        "id2",
        wait=False,
        timeout=None,
        poll_interval=None,
    )


def test_run_cli_invalid_selection():
    def fake_input(prompt):
        return "99"

    client = Mock()
    jobs = [("job1", "id1")]
    with pytest.raises(ValueError, match="Invalid job number"):
        cli.run_cli(
            job_name=None,
            wait=False,
            timeout=None,
            poll_interval=None,
            activity=False,
            client=client,
            jobs=jobs,
            input_fn=fake_input,
        )


def test_run_returns_0_on_success(monkeypatch):
    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", lambda **kwargs: "execution_successful")
    args = cli.parse_args(["--job", "job1"])
    assert cli.run(args) == 0


@pytest.mark.parametrize(
    "status",
    [
        "deploy_failed",
        "execution_rejected",
        "execution_failed",
        "terminated",
        "terminated_timeout",
        "terminated_shutdown",
    ],
)
def test_run_returns_1_on_failure(monkeypatch, status):
    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", lambda **kwargs: status)
    args = cli.parse_args(["--job", "job1"])
    assert cli.run(args) == 1


@pytest.mark.parametrize(
    "missing_var",
    [
        pytest.param("ACCESS_TOKEN", id="access_token"),
        pytest.param("API_URL", id="api_url"),
    ],
)
def test_run_returns_2_on_missing_env_var(monkeypatch, missing_var):
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.delenv(missing_var, raising=False)
    args = cli.parse_args(["--job", "job1"])
    assert cli.run(args) == 2


def test_run_returns_2_on_invalid_args(monkeypatch):
    monkeypatch.setattr(cli, "validate_args", lambda args: "Error: some error")
    monkeypatch.setattr(cli, "TalendClient", Mock())
    monkeypatch.setattr(cli, "run_cli", Mock())
    args = Mock()
    assert cli.run(args) == 2


def test_run_returns_130_on_keyboard_interrupt(monkeypatch):
    def boom(**kwargs):
        raise KeyboardInterrupt()

    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", boom)
    args = cli.parse_args(["--job", "job1"])
    assert cli.run(args) == 130


def test_run_parses_args_and_passes_values(monkeypatch):
    def fake_run_cli(**kwargs):
        called.update(kwargs)
        return "execution_successful"

    called = {}
    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", fake_run_cli)
    args = cli.parse_args(["--wait", "--poll-interval", "10", "--job", "job1"])
    assert cli.run(args) == 0
    assert called["wait"] is True
    assert called["job_name"] == "job1"
    assert called["poll_interval"] == 10


def test_run_rejects_timeout_without_wait(monkeypatch):
    args = cli.parse_args(["--timeout", "10"])
    assert cli.run(args) == 2


def test_run_rejects_poll_interval_without_wait(monkeypatch):
    args = cli.parse_args(["--poll-interval", "10"])
    assert cli.run(args) == 2


def test_main_exits_with_code_from_run(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setattr(cli, "run", lambda args: 0)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
