# Copyright (c) 2026 Corey Goldberg
# License: MIT


"""Tests for talend_task CLI."""

from unittest.mock import Mock

import pytest

from talend_task import cli


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
    status, elapsed = cli.run_job(
        client,
        "job123",
        wait=False,
    )
    assert status == "submitted"
    assert elapsed is None
    client.run.assert_called_once_with("job123")


def test_run_job_wait(monkeypatch):
    client = Mock()
    client.run.return_value = "execution_successful"
    times = iter([100.0, 165.0])
    monkeypatch.setattr(
        "talend_task.cli.time.time",
        lambda: next(times),
    )
    status, elapsed = cli.run_job(
        client,
        "job123",
        wait=True,
    )
    assert status == "execution_successful"
    assert elapsed == "00:01:05"


def test_run_cli_named_job_success():
    client = Mock()
    jobs = [
        ("job1", "id1"),
        ("job2", "id2"),
    ]
    run_job_mock = Mock(return_value=("execution_successful", None))
    status, elapsed = cli.run_cli(
        job_name="job2",
        wait_enabled=False,
        client=client,
        jobs=jobs,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_successful"
    assert elapsed is None
    run_job_mock.assert_called_once_with(
        client,
        "id2",
        wait=False,
    )


def test_run_cli_named_job_fail():
    client = Mock()
    jobs = [
        ("job1", "id1"),
        ("job2", "id2"),
    ]
    run_job_mock = Mock(return_value=("execution_failed", None))
    status, elapsed = cli.run_cli(
        job_name="job1",
        wait_enabled=False,
        client=client,
        jobs=jobs,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_failed"
    assert elapsed is None
    run_job_mock.assert_called_once_with(
        client,
        "id1",
        wait=False,
    )


def test_run_cli_invalid_job():
    client = Mock()
    jobs = [
        ("job1", "id1"),
    ]
    with pytest.raises(ValueError, match="Invalid job"):
        cli.run_cli(
            job_name="does_not_exist",
            wait_enabled=False,
            client=client,
            jobs=jobs,
        )


def test_run_cli_interactive_selection():
    def fake_input(prompt):
        return "2"

    client = Mock()
    jobs = [
        ("job1", "id1"),
        ("job2", "id2"),
    ]
    run_job_mock = Mock(return_value=("execution_successful", None))
    status, elapsed = cli.run_cli(
        job_name=None,
        wait_enabled=False,
        client=client,
        jobs=jobs,
        input_fn=fake_input,
        run_job_fn=run_job_mock,
    )
    assert status == "execution_successful"
    assert elapsed is None
    run_job_mock.assert_called_once_with(
        client,
        "id2",
        wait=False,
    )


def test_run_cli_invalid_selection():
    def fake_input(prompt):
        return "99"

    client = Mock()
    jobs = [
        ("job1", "id1"),
    ]
    with pytest.raises(ValueError, match="Invalid job number"):
        cli.run_cli(
            job_name=None,
            wait_enabled=False,
            client=client,
            jobs=jobs,
            input_fn=fake_input,
        )


def test_main_parses_args(monkeypatch):
    class Args:
        job = "job1"
        wait = True

    fake_client = Mock(get_jobs=lambda: [("job1", "id1")])
    monkeypatch.setattr(cli, "parse_args", lambda: Args())
    monkeypatch.setattr(cli, "require_env", lambda name: "value")
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", lambda **kwargs: ("execution_successful", None))
    cli.main()


def test_main_sucess(monkeypatch):
    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(cli, "parse_args", lambda: Mock(job="job1", wait=False))
    monkeypatch.setenv("ACCESS_TOKEN", "token")
    monkeypatch.setenv("API_URL", "https://example.com")
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", lambda **kwargs: ("execution_successful", None))
    cli.main()


def test_main_exits_on_failure(monkeypatch):
    fake_client = Mock()
    fake_client.get_jobs.return_value = [("job1", "id1")]
    monkeypatch.setattr(cli, "parse_args", lambda: Mock(job="job1", wait=False))
    monkeypatch.setenv("ACCESS_TOKEN", "token")
    monkeypatch.setenv("API_URL", "https://example.com")
    monkeypatch.setattr(cli, "TalendClient", lambda *args: fake_client)
    monkeypatch.setattr(cli, "run_cli", lambda **kwargs: ("execution_failed", None))
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 1
