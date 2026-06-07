# Copyright (c) 2026 Corey Goldberg
# License: MIT


import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

from .talend_client import TalendClient

logger = logging.getLogger(__name__)


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def convert_time(seconds):
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02.0f}:{mins:02.0f}:{secs:02.0f}"


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


def select_job(jobs, input_fn=input):
    logger.info("\nAvailable Talend Jobs:")
    logger.info("----------------------")
    for num, job in enumerate(jobs, 1):
        logger.info("%s %s", num, job[0])
    job_number = input_fn("\nSelect a job number to run: ")
    try:
        job_number = int(job_number)
        if job_number < 1 or job_number > len(jobs):
            raise ValueError()
    except ValueError:
        raise ValueError("Invalid job number")
    return jobs[job_number - 1]


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
        logger.info("\nExecuting job: %s", job_name)
        return run_job_fn(client, job_id, poll_interval=poll_interval, wait=wait)
    job_name, job_id = select_job(jobs, input_fn=input_fn)
    logger.info("\nExecuting job: %s", job_name)
    return run_job_fn(client, job_id, poll_interval=poll_interval, wait=wait)


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
        help="polling interval in seconds (requires --wait) (default: 5)",
    )
    return parser


def parse_args(argv=None):
    parser = create_parser()
    return parser.parse_args(argv)


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(message)s (%(asctime)s)",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
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
        status, elapsed = run_cli(
            job_name=args.job,
            wait=args.wait,
            poll_interval=args.poll_interval,
            client=client,
            jobs=jobs,
        )
        if args.wait:
            logger.info("\nExecution finished")
            logger.info("Status: '%s' (duration: %s)", status, elapsed)
        if status != "execution_successful":
            sys.exit(1)
    except ValueError as e:
        logger.error("Error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Exiting")
        sys.exit(130)
