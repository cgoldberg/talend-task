#!/usr/bin/env python
#
# Copyright (c) 2026 Corey Goldberg
# License: MIT


"""CLI for running ETL jobs (tasks) remotely via Talend Cloud API."""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv
from rich.progress import Progress, TimeElapsedColumn

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


load_dotenv()
try:
    ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
    API_URL = os.environ["API_URL"]
except KeyError as e:
    raise RuntimeError(f".env file or environment variables must be set. Missing: {e}")

BASE_URL = urljoin(API_URL, "processing")


def _convert_time(seconds):
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02.0f}:{mins:02.0f}:{secs:02.0f}"


def _send_request(url, payload=None):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    if payload:
        response = requests.post(url, headers=headers, json=payload)
    else:
        response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_jobs():
    url = f"{BASE_URL}/executables/tasks"
    result = _send_request(url)
    jobs = [(item["name"], item["executable"]) for item in result["items"]]
    return jobs


def run_talend_job(job_id):
    url = f"{BASE_URL}/executions"
    payload = {"executable": job_id}
    result = _send_request(url, payload)
    exec_id = result["executionId"]
    return exec_id


def get_execution_status(execution_id):
    url = f"{BASE_URL}/executions/{execution_id}"
    result = _send_request(url)
    status = result["status"]
    return status


def run_console(job_id):
    exec_id = run_talend_job(job_id)
    columns = (*Progress.get_default_columns(), TimeElapsedColumn())
    with Progress(*columns, transient=True) as progress:
        task = progress.add_task("twiddling thumbs ", total=None)
        while True:
            status = get_execution_status(exec_id)
            if status not in ("dispatching", "executing"):
                return status
            else:
                time.sleep(5)
            progress.advance(task)


def run_unnatended(job_id):
    exec_id = run_talend_job(job_id)
    while True:
        status = get_execution_status(exec_id)
        logger.info(
            f"status: {status} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        )
        if status not in ("dispatching", "executing"):
            return status
        else:
            time.sleep(10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wait",
        action="store_true",
        help="wait for task to complete and show status",
    )
    parser.add_argument(
        "--job",
        help="Talend ETL task name",
    )
    args = parser.parse_args()
    job_name = args.job
    wait_enabled = args.wait
    jobs = get_jobs()
    if job_name:
        if job_name not in (job[0] for job in jobs):
            sys.exit(f"Invalid ETL job: {job_name}")
        job_id = next(job[1] for job in jobs if job[0] == job_name)
        logger.info(f"\nExecuting job: '{job_name}' ....")
        if wait_enabled:
            start = time.time()
            status = run_unnatended(job_id)
            stop = time.time()
            elapsed = _convert_time(stop - start)
            logger.info(f"\nExecution of job '{job_name}' finished")
            logger.info(f"status: '{status}' (time: {elapsed})")
        else:
            run_talend_job(job_id)
    else:
        try:
            logger.info("\nAvailable ETL Jobs:")
            logger.info("-------------------")
            for num, job in enumerate(jobs, 1):
                logger.info(f"{num}) {job[0]}")
            job_number = input("\nSelect a job number to run: ")
            try:
                job_number = int(job_number)
                if job_number > len(jobs):
                    raise ValueError()
            except ValueError:
                raise ValueError("Invalid job number!")
            job_name, job_id = jobs[job_number - 1]
            logger.info(f"\nExecuting job: {job_name} ({job_id})\n")
            if wait_enabled:
                start = time.time()
                status = run_console(job_id)
                stop = time.time()
                elapsed = _convert_time(stop - start)
                logger.info(
                    f"\nExecution finished with status: '{status}' (time: {elapsed})"
                )
                input("\nPress <Enter> to exit...")
            else:
                run_talend_job(job_id)
        except (Exception, KeyboardInterrupt) as e:
            input(f"\n{e}\nPress <Enter> to exit...")
            sys.exit()


if __name__ == "__main__":
    main()
