# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


import argparse
import sys
from unittest.mock import Mock

import pytest

from talend_task import cli


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


def test_parse_defaults():
    args = cli.parse_args([])
    assert args.debug is False
    assert args.wait is False
    assert args.job is None
    assert args.timeout is None
    assert args.poll_interval is None


def test_parse_flags():
    args = cli.parse_args(
        ["--wait", "--timeout", "30", "--poll-interval", "10", "--job", "job1"]
    )
    assert args.wait is True
    assert args.timeout == 30
    assert args.poll_interval == 10
    assert args.job == "job1"


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(
            argparse.Namespace(timeout=None, poll_interval=None, wait=False),
            id="defaults",
        ),
        pytest.param(
            argparse.Namespace(timeout=1, poll_interval=None, wait=True),
            id="wait_timeout",
        ),
        pytest.param(
            argparse.Namespace(timeout=None, poll_interval=1, wait=True),
            id="wait_poll",
        ),
        pytest.param(
            argparse.Namespace(timeout=1, poll_interval=1, wait=True),
            id="wait_timeout_and_poll",
        ),
    ],
)
def test_validate_args_valid(args):
    assert cli.validate_args(args) is None


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(
            argparse.Namespace(timeout=0, poll_interval=None, wait=True),
            id="timeout_zero",
        ),
        pytest.param(
            argparse.Namespace(timeout=None, poll_interval=0, wait=True),
            id="poll_zero",
        ),
        pytest.param(
            argparse.Namespace(timeout=-1, poll_interval=None, wait=True),
            id="timeout_negative",
        ),
        pytest.param(
            argparse.Namespace(timeout=None, poll_interval=-1, wait=True),
            id="poll_negative",
        ),
        pytest.param(
            argparse.Namespace(timeout=1, poll_interval=None, wait=False),
            id="timeout_requires_wait",
        ),
        pytest.param(
            argparse.Namespace(timeout=None, poll_interval=1, wait=False),
            id="poll_requires_wait",
        ),
    ],
)
def test_validate_args_invalid(args):
    result = cli.validate_args(args)
    assert isinstance(result, str)


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
    jobs = [("job1", "id1"), ("job2", "id2")]
    run_job_mock = Mock(return_value=("execution_successful", None))
    status = cli.run_cli(
        job_name="job2",
        wait=False,
        timeout=None,
        poll_interval=None,
        client=client,
        jobs=jobs,
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


def test_run_cli_named_job_fail():
    client = Mock()
    jobs = [("job1", "id1"), ("job2", "id2")]
    run_job_mock = Mock(return_value=("execution_failed", None))
    status = cli.run_cli(
        job_name="job1",
        wait=False,
        timeout=None,
        poll_interval=None,
        client=client,
        jobs=jobs,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_failed"
    run_job_mock.assert_called_once_with(
        client,
        "id1",
        wait=False,
        timeout=None,
        poll_interval=None,
    )


def test_run_cli_invalid_job():
    client = Mock()
    jobs = [("job1", "id1")]
    unknown_job = "does_not_exist"
    with pytest.raises(ValueError, match=f"Invalid job: {unknown_job}"):
        cli.run_cli(
            job_name=unknown_job,
            wait=False,
            timeout=None,
            poll_interval=None,
            client=client,
            jobs=jobs,
        )


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
        "execution_failed",
        "execution_canceled",
        "execution_terminated",
        "execution_rejected",
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


@pytest.mark.parametrize(
    "argv",
    [
        ["--timeout", "30"],
        ["--poll-interval", "10"],
        ["--timeout", "-1"],
        ["--poll-interval", "-1"],
        ["--timeout", "30", "--poll-interval", "10"],
    ],
)
def test_run_returns_2_on_invalid_args(monkeypatch, argv):
    fake_client = Mock()
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", lambda **kwargs: "execution_successful")
    args = cli.parse_args(argv)
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
