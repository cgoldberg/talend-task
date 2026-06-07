# Copyright (c) 2026 Corey Goldberg
# License: MIT


import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .talend_client import TalendClient

logger = logging.getLogger(__name__)
console = Console()


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def convert_time(seconds):
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02.0f}:{mins:02.0f}:{secs:02.0f}"


def select_job(jobs, input_fn=input):
    console.print()
    table = Table(title="[bold]Talend Cloud Jobs[/bold]")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Job Name", style="green")
    for num, job in enumerate(jobs, 1):
        table.add_row(str(num), job[0])
    console.print(table)
    job_number = input_fn("\nSelect a job number to run: ")
    try:
        job_number = int(job_number)
        if job_number < 1 or job_number > len(jobs):
            raise ValueError()
    except ValueError:
        raise ValueError("Invalid job number")
    return jobs[job_number - 1]


def run_job(client, job_id, poll_interval, wait=True):
    if not wait:
        status = client.run(job_id)
        return status, None
    else:
        start = time.monotonic()
        status = client.run(job_id, poll_interval=poll_interval, wait=True)
        stop = time.monotonic()
        elapsed_time = convert_time(stop - start)
        return status, elapsed_time


def run_cli(
    job_name,
    wait,
    poll_interval,
    client,
    jobs,
    input_fn=input,
    run_job_fn=None,
):
    if run_job_fn is None:
        run_job_fn = run_job
    if job_name:
        if job_name not in (job[0] for job in jobs):
            raise ValueError(f"Invalid job: {job_name}")
        job_id = next(job[1] for job in jobs if job[0] == job_name)
        logger.info("Executing job: %s", job_name)
        status, elapsed_time = run_job_fn(
            client,
            job_id,
            poll_interval=poll_interval,
            wait=wait,
        )
        return status
    job_name, job_id = select_job(jobs, input_fn=input_fn)
    console.print()
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
        poll_interval=poll_interval,
        wait=wait,
    )
    console.print()
    if wait:
        console.print(
            Panel.fit(
                f"[bold green]✓ Completed[/bold green]\n"
                f"[bold]Job:[/bold] {job_name}\n"
                f"[bold]Duration:[/bold] {elapsed_time}",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[bold green]✓ Submitted[/bold green]\n[bold]Job:[/bold] {job_name}",
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
        help="wait for job to complete and show status",
    )
    parser.add_argument(
        "--job",
        help="job name",
    )
    parser.add_argument(
        "--poll-interval",
        default=None,
        type=int,
        metavar="SECS",
        help="polling interval (requires --wait) (default: 5)",
    )
    return parser


def parse_args(argv=None):
    parser = create_parser()
    return parser.parse_args(argv)


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
        stream=sys.stdout,
    )
    try:
        if args.poll_interval is not None and not args.wait:
            logger.error("Error: --poll-interval requires --wait")
            sys.exit(1)
        load_dotenv()
        access_token = require_env("ACCESS_TOKEN")
        api_url = require_env("API_URL")
        client = TalendClient(api_url, access_token)
        jobs = client.get_jobs()
        status = run_cli(
            job_name=args.job,
            wait=args.wait,
            poll_interval=args.poll_interval,
            client=client,
            jobs=jobs,
        )
        if args.wait:
            logger.info("Execution finished")
        if status != "execution_successful":
            sys.exit(1)
    except ValueError as e:
        logger.error("Error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Exiting")
        sys.exit(130)
