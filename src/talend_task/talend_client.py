# Copyright (c) 2026 Corey Goldberg
# License: MIT


import logging
import time
from datetime import datetime
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


HTTP_TIMEOUT = 30


class TalendClient:
    def __init__(self, api_url, access_token):
        self.access_token = access_token
        self.base_url = urljoin(api_url, "processing")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        )

    def _get(self, path):
        resp = self.session.get(
            f"{self.base_url}{path}",
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, payload):
        resp = self.session.post(
            f"{self.base_url}{path}",
            json=payload,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def get_jobs(self):
        result = self._get("/executables/tasks")
        return [(item["name"], item["executable"]) for item in result["items"]]

    def get_job_id(self, job_name):
        jobs = self.get_jobs()
        if job_name not in jobs:
            raise ValueError(f"Talend job not found: {job_name}")
        return jobs[job_name]

    def get_execution_status(self, execution_id):
        result = self._get(f"/executions/{execution_id}")
        status = result["status"]
        return status

    def run_job(self, job_id):
        result = self._post(
            "/executions",
            {"executable": job_id},
        )
        execution_id = result["executionId"]
        logging.info(
            "Talend job submitted: %s, executionId=%s",
            job_id,
            execution_id,
        )
        return execution_id

    def run(self, job_id, wait=False, poll_interval=5):
        status = "uknown"
        exec_id = self.run_job(job_id)
        if not wait:
            return status
        else:
            while True:
                status = self.get_execution_status(exec_id)
                logger.info(
                    f"Status: {status} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
                )
                if status in ("dispatching", "executing"):
                    time.sleep(poll_interval)
                else:
                    return status
