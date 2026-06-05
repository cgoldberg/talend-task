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


def _convert_time(seconds):
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02.0f}:{mins:02.0f}:{secs:02.0f}"


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wait",
        action="store_true",
        help="wait for task to complete and show status",
    )
    parser.add_argument(
        "--job",
        help="task name",
    )
    return parser.parse_args()


def _require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main():
    args = _parse_args()
    job_name = args.job
    wait_enabled = args.wait

    load_dotenv()
    access_token = _require_env("ACCESS_TOKEN")
    api_url = _require_env("API_URL")

    client = TalendClient(api_url, access_token)
    jobs = client.get_jobs()
    print(jobs)
    if job_name:
        if job_name not in (job[0] for job in jobs):
            sys.exit(f"Invalid ETL job: {job_name}")
        job_id = next(job[1] for job in jobs if job[0] == job_name)
        logger.info(f"\nExecuting job: '{job_name}' ....")
        if wait_enabled:
            start = time.time()
            status = client.run(job_id, wait=True)
            stop = time.time()
            elapsed = _convert_time(stop - start)
            if status != "execution_successful":
                sys.exit(1)
        else:
            client.run(job_id)
    else:
        try:
            logger.info("\nAvailable Talend Jobs:")
            logger.info("----------------------")
            for num, job in enumerate(jobs, 1):
                logger.info(f"{num}) {job[0]}")
            job_number = input("\nSelect a job number to run: ")
            try:
                job_number = int(job_number)
                if job_number > len(jobs):
                    raise ValueError()
            except ValueError:
                raise ValueError("Invalid job number")
            job_name, job_id = jobs[job_number - 1]
            logger.info(f"\nExecuting job: {job_name} ({job_id})\n")
            if wait_enabled:
                start = time.time()
                status = client.run(job_id, progress_bar=True, wait=True)
                stop = time.time()
                elapsed = _convert_time(stop - start)
                if status != "execution_successful":
                    sys.exit(1)
            else:
                client.run(job_id)
        except KeyboardInterrupt as e:
            logger.error(e)
            sys.exit(1)
    if wait_enabled:
        logger.info("\nExecution finished")
        logger.info(f"Status: '{status}' (time: {elapsed})")
