"""
Talend Cloud CLI for executing and monitoring jobs via Talend Cloud Processing
API.

This module provides a command-line interface for discovering, running, and
monitoring Talend Cloud jobs using the TalendClient API wrapper. It supports
interactive job selection, direct execution by name, and optional synchronous
waiting with status polling.

Features:

- Run jobs interactively or via --job argument
- Optional blocking mode with polling and timeout support
- View recent execution history without triggering runs (--activity)
- Rich terminal output using tables and panels
- Environment-based configuration via .env (API_URL, ACCESS_TOKEN)
- Structured logging with optional debug mode

Configuration:

- API_URL: Talend Cloud Processing API base URL
- ACCESS_TOKEN: bearer token for authentication

Exit codes:

- 0 success
- 1 execution or runtime failure
- 2 configuration or validation error
- 130 user interrupt (Ctrl+C)
"""

# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT

import argparse
import logging
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .talend_client import DEFAULT_POLL_INTERVAL, TalendClient

logger = logging.getLogger(__name__)
console = Console()


class ConfigError(Exception):
    pass


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def format_iso_timestamp(timestamp):
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return dt.strftime("%m/%d/%Y %I:%M %p")


def convert_time(seconds):
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02.0f}:{mins:02.0f}:{secs:02.0f}"


def compute_duration(start_timestamp, end_timestamp):
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    start_dt = datetime.strptime(start_timestamp, fmt)
    end_dt = datetime.strptime(end_timestamp, fmt)
    elapsed_secs = (end_dt - start_dt).total_seconds()
    return convert_time(elapsed_secs)


def show_activity(job_name, executions):
    console.print()
    table = Table(title=f"[bold]Job Activity: {job_name}[/bold]")
    table.add_column("Status")
    table.add_column("End Time", style="cyan")
    table.add_column("Duration", style="yellow")
    table.add_column("Version", style="cyan")
    table.add_column("Runtime", style="white")
    table.add_column("Triggered By", style="white")
    for execution in executions:
        status = execution["execution_status"].removeprefix("EXECUTION_")
        if not execution.get("finish_timestamp"):
            status_text = Text(status, style="yellow")
        elif "SUCCESS" in status:
            status_text = Text(status, style="green")
        elif "FAIL" in status:
            status_text = Text(status, style="red")
        else:
            status_text = Text(status, style="white")
        if execution.get("finish_timestamp"):
            start_timestamp = execution["start_timestamp"]
            end_timestamp = execution["finish_timestamp"]
            end_time = format_iso_timestamp(end_timestamp)
            duration = compute_duration(start_timestamp, end_timestamp)
        else:
            end_time = ""
            duration = ""
        table.add_row(
            status_text,
            end_time,
            duration,
            execution["task_version"],
            execution["runtime_type"],
            execution["user_id"],
        )
    console.print(table)


def select_job(jobs, input_fn=input):
    console.print()
    table = Table(title="[bold]Talend Cloud Jobs[/bold]")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Job Name", style="green")
    for num, job in enumerate(jobs, 1):
        table.add_row(str(num), job[0])
    console.print(table)
    job_number = input_fn("\nSelect a job number: ")
    try:
        job_number = int(job_number)
        if job_number < 1 or job_number > len(jobs):
            raise ValueError()
    except ValueError:
        raise ValueError("Invalid job number")
    return jobs[job_number - 1]


def run_job(client, job_id, timeout, poll_interval, wait=True):
    if not wait:
        status = client.run(job_id)
        return status, None
    else:
        start = time.monotonic()
        status = client.run(
            job_id,
            wait=True,
            timeout=timeout,
            poll_interval=poll_interval,
        )
        stop = time.monotonic()
        elapsed_time = convert_time(stop - start)
        return status, elapsed_time


def run_cli(
    job_name,
    wait,
    timeout,
    poll_interval,
    activity,
    client,
    jobs,
    input_fn=input,
    run_job_fn=None,
):
    if run_job_fn is None:
        run_job_fn = run_job

    if job_name:
        job_id = client.get_job_id(job_name)
        if activity:
            job_id = client.get_job_id(job_name)
            executions = client.get_executions(job_id)
            show_activity(job_name, executions)
            return
        logger.info("Executing job: %s", job_name)
        status, elapsed_time = run_job_fn(
            client,
            job_id,
            timeout=timeout,
            poll_interval=poll_interval,
            wait=wait,
        )
        if wait:
            logger.info("Duration: %s", elapsed_time)
            logger.info("Execution finished")
        return status
    job_name, job_id = select_job(jobs, input_fn=input_fn)
    if activity:
        job_id = client.get_job_id(job_name)
        executions = client.get_executions(job_id)
        show_activity(job_name, executions)
        return
    console.print(
        Panel.fit(
            f"[bold green]{job_name}[/bold green]",
            title="Executing Job",
        )
    )
    logger.info("Executing job: %s", job_name)
    status, elapsed_time = run_job_fn(
        client,
        job_id,
        timeout=timeout,
        poll_interval=poll_interval,
        wait=wait,
    )
    if wait:
        completed_msg = (
            "[bold green]✓ Completed[/bold green]\n"
            if status == "execution_successful"
            else "[bold red]✗ Completed with errors[/bold red]\n"
        )
        console.print(
            Panel.fit(
                completed_msg
                + f"[bold]Job:[/bold] {job_name}\n"
                + f"[bold]Duration:[/bold] {elapsed_time}",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                "[bold green]✓ Submitted[/bold green]\n"
                + f"[bold]Job:[/bold] {job_name}",
                border_style="green",
            )
        )
    return status


def create_parser():
    def formatter(prog):
        return argparse.HelpFormatter(
            prog,
            width=100,
            max_help_position=35,
        )

    parser = argparse.ArgumentParser(
        description="Talend Cloud CLI",
        formatter_class=formatter,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable debug logging",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="wait for job to complete and return status",
    )
    parser.add_argument(
        "--activity",
        action="store_true",
        help="show recent runs without executing job (cannot be used with --wait)",
    )
    parser.add_argument(
        "--job",
        metavar="NAME",
        help="job name",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SECS",
        help="timeout (requires --wait, default: none)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=None,
        metavar="SECS",
        help=f"polling interval (requires --wait, default: {DEFAULT_POLL_INTERVAL})",
    )
    return parser


def parse_args(argv=None):
    parser = create_parser()
    return parser.parse_args(argv)


def validate_args(args):
    if args.timeout is not None and args.timeout < 1:
        return "--timeout must be >= 1"
    if args.poll_interval is not None and args.poll_interval < 1:
        return "--poll-interval must be >= 1"
    if args.activity:
        if args.wait:
            return "--activity cannot be used with --wait"
        if args.poll_interval is not None:
            return "--activity cannot be used with --poll-interval"
        if args.timeout is not None:
            return "--activity cannot be used with --timeout"
        return None  # activity mode is valid on its own
    if args.poll_interval is not None and not args.wait:
        return "--poll-interval requires --wait"
    if args.timeout is not None and not args.wait:
        return "--timeout requires --wait"
    return None


def run(args):
    try:
        error = validate_args(args)
        if error:
            logger.error(error)
            return 2
        load_dotenv()
        access_token = require_env("ACCESS_TOKEN")
        api_url = require_env("API_URL")
        client = TalendClient(api_url, access_token)
        jobs = client.get_jobs()
        status = run_cli(
            job_name=args.job,
            timeout=args.timeout,
            wait=args.wait,
            poll_interval=args.poll_interval,
            activity=args.activity,
            client=client,
            jobs=jobs,
        )
        if status not in ("execution_successful", "unknown"):
            logger.exception("Execution not succesful")
            return 1
    except ConfigError as e:
        if args.debug:
            raise
        logger.error("Config error: %s", e)
        return 2
    except KeyboardInterrupt:
        logger.info("Exiting")
        return 130
    except Exception:
        if args.debug:
            raise
        logger.exception("Unexpected error")
        return 1
    return 0


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
        stream=sys.stdout,
    )
    sys.exit(run(args))
