# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


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
    with pytest.raises(RuntimeError) as exc:
        cli.require_env("DOES_NOT_EXIST")
    assert "Missing required environment variable" in str(exc.value)


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        pytest.param(0, "00:00:00", id="zero"),
        pytest.param(5, "00:00:05", id="seconds"),
        pytest.param(65, "00:01:05", id="minutes"),
        pytest.param(3661, "01:01:01", id="hours"),
    ],
)
def test_convert_time(seconds, expected):
    assert cli.convert_time(seconds) == expected


def test_run_job_no_wait():
    client = Mock()
    client.run.return_value = "submitted"
    status, elapsed_time = cli.run_job(client, "job123", wait=False, poll_interval=None)
    assert status == "submitted"
    assert elapsed_time is None
    client.run.assert_called_once_with("job123")


def test_run_job_wait(monkeypatch):
    client = Mock()
    client.run.return_value = "execution_successful"
    times = iter([100.0, 165.0])
    monkeypatch.setattr("talend_task.cli.time.monotonic", lambda: next(times))
    status, elapsed_time = cli.run_job(client, "job123", wait=True, poll_interval=5)
    assert status == "execution_successful"
    assert elapsed_time == "00:01:05"


def test_run_cli_named_job_success():
    client = Mock()
    jobs = [("job1", "id1"), ("job2", "id2")]
    run_job_mock = Mock(return_value=("execution_successful", None))
    status = cli.run_cli(
        job_name="job2",
        wait=False,
        poll_interval=None,
        client=client,
        jobs=jobs,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_successful"
    run_job_mock.assert_called_once_with(client, "id2", wait=False, poll_interval=None)


def test_run_cli_named_job_fail():
    client = Mock()
    jobs = [("job1", "id1"), ("job2", "id2")]
    run_job_mock = Mock(return_value=("execution_failed", None))
    status = cli.run_cli(
        job_name="job1",
        wait=False,
        poll_interval=None,
        client=client,
        jobs=jobs,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_failed"
    run_job_mock.assert_called_once_with(client, "id1", wait=False, poll_interval=None)


def test_run_cli_invalid_job():
    client = Mock()
    jobs = [("job1", "id1")]
    with pytest.raises(ValueError, match="Invalid job"):
        cli.run_cli(
            job_name="does_not_exist",
            wait=False,
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
        poll_interval=None,
        client=client,
        jobs=jobs,
        input_fn=fake_input,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_successful"
    run_job_mock.assert_called_once_with(client, "id2", wait=False, poll_interval=None)


def test_run_cli_invalid_selection():
    def fake_input(prompt):
        return "99"

    client = Mock()
    jobs = [("job1", "id1")]
    with pytest.raises(ValueError, match="Invalid job number"):
        cli.run_cli(
            job_name=None,
            wait=False,
            poll_interval=None,
            client=client,
            jobs=jobs,
            input_fn=fake_input,
        )


def test_main_success(monkeypatch):
    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(sys, "argv", ["prog", "--job", "job1"])
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", lambda **kwargs: "execution_successful")
    cli.main()


def test_main_exits_on_failure(monkeypatch):
    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(sys, "argv", ["prog", "--job", "job1"])
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", lambda **kwargs: "execution_failed")
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1


def test_main_keyboard_interrupt(monkeypatch):
    def boom(**kwargs):
        raise KeyboardInterrupt()

    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(sys, "argv", ["prog", "--job", "job1"])
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", boom)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 130


def test_main_parses_args_and_passes_values(monkeypatch):
    def fake_run_cli(**kwargs):
        called.update(kwargs)
        return "execution_successful"

    called = {}
    fake_client = Mock(get_jobs=lambda: [("job1", "id1")])
    monkeypatch.setattr(
        sys, "argv", ["prog", "--wait", "--poll-interval", "10", "--job", "job1"]
    )
    monkeypatch.setattr(cli, "require_env", lambda name: "value")
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", fake_run_cli)
    cli.main()
    assert called["wait"] is True
    assert called["job_name"] == "job1"
    assert called["poll_interval"] == 10


def test_main_rejects_poll_interval_without_wait(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--poll-interval", "10"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1


def test_parse_args_defaults_without_optional_flags():
    args = cli.parse_args(["--job", "job1"])
    assert args.job == "job1"
    assert args.debug is False
    assert args.wait is False
    assert args.poll_interval is None


def test_parse_args_with_debug_flag_sets_true():
    args = cli.parse_args(["--debug", "--job", "job1"])
    assert args.debug is True


def test_parse_args_with_wait_and_poll_interval_parses_successfully():
    args = cli.parse_args(["--wait", "--poll-interval", "10"])
    assert args.wait is True
    assert args.poll_interval == 10
