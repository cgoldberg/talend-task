# Copyright (c) 2026 Corey Goldberg
# License: MIT


import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

from .talend_client import TalendClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
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


def run_job(client, job_id, wait=True):
    if not wait:
        status = client.run(job_id)
        return status, None
    else:
        start = time.time()
        status = client.run(job_id, wait=True)
        stop = time.time()
        elapsed_time = convert_time(stop - start)
        return status, elapsed_time


def select_job(jobs, input_fn=input):
    logger.info("\nAvailable Talend Jobs:")
    logger.info("----------------------")
    for num, job in enumerate(jobs, 1):
        logger.info(f"{num}) {job[0]}")
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
    wait_enabled,
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
        logger.info(f"\nExecuting job: {job_name}")
        return run_job_fn(client, job_id, wait=wait_enabled)
    job_name, job_id = select_job(jobs, input_fn=input_fn)
    return run_job_fn(client, job_id, wait=wait_enabled)


def parse_args():
    parser = argparse.ArgumentParser(description="Talend Cloud CLI")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable debug logging",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="wait for task to complete and show status",
    )
    parser.add_argument(
        "--job",
        help="job name",
    )
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        level = logging.DEBUG if args.debug else logging.INFO
        logging.basicConfig(level=level, format="%(message)s", force=True)
        logger = logging.getLogger(__name__)
        logger.debug("Debug logging enabled")
        load_dotenv()
        access_token = require_env("ACCESS_TOKEN")
        api_url = require_env("API_URL")
        client = TalendClient(api_url, access_token)
        jobs = client.get_jobs()
        try:
            status, elapsed = run_cli(
                job_name=args.job,
                wait_enabled=args.wait,
                client=client,
                jobs=jobs,
            )
        except ValueError:
            logger.exception("CLI failed")
            sys.exit(1)
        if args.wait:
            logger.info("\nExecution finished")
            logger.info(f"Status: '{status}' (time: {elapsed})")
        if status != "execution_successful":
            sys.exit(1)
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Exiting")
        sys.exit(130)
