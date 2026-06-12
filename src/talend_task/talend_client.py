# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


import logging
import time

import requests

logger = logging.getLogger(__name__)


TALEND_API_VERSION = "2021-03"
HTTP_TIMEOUT = 30


class TalendClient:
    def __init__(self, api_url, access_token):
        self.access_token = access_token
        self.base_url = api_url.rstrip("/") + "/processing"
        self.session = AuthSession(access_token)
        self._jobs_cache = None

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

    def _jobs(self):
        if self._jobs_cache is None:
            result = self._get("/executables/tasks")
            self._jobs_cache = result.get("items", [])
        return self._jobs_cache

    def get_jobs(self):
        return [(item["name"], item["executable"]) for item in self._jobs()]

    def get_job_id(self, job_name):
        job_id = next(
            (item["executable"] for item in self._jobs() if item["name"] == job_name),
            None,
        )
        if job_id is None:
            raise ValueError(f"Unknown job: {job_name}")
        return job_id

    def get_execution_status(self, execution_id):
        """Get current execution status.

        Jobs are dispatched and validated, then executed if accepted, and
        finally transition to a terminal state indicating success, failure,
        rejection, or termination reason.

        Execution lifecycle of a task from request to completion:

        REQUEST
           ↓
        dispatching
           ├── deploy_failed
           ├── execution_rejected
           └── executing
                   ├── execution_successful
                   ├── execution_failed
                   ├── terminated
                   ├── terminated_timeout
                   └── terminated_shutdown
        """
        result = self._get(f"/executions/{execution_id}")
        status = result["status"]
        return status

    def get_executions(self, job_id, limit=20):
        result = self._get(f"/executables/tasks/{job_id}/executions")
        items = result.get("items", [])
        executions = [
            {
                "execution_status": item.get("executionStatus"),
                "start_timestamp": item.get("startTimestamp"),
                "finish_timestamp": item.get("finishTimestamp"),
                "task_version": item.get("taskVersion"),
                "runtime_type": item.get("runtime", {}).get("type"),
                "user_id": item.get("userId"),
            }
            for item in items
        ]
        executions = sorted(
            executions, key=lambda x: x.get("start_timestamp") or "", reverse=True
        )[:limit]
        return executions

    def run_job(self, job_id):
        result = self._post("/executions", {"executable": job_id})
        execution_id = result["executionId"]
        logger.info(
            "Job submitted\n    jobId       : %s\n    executionId : %s",
            job_id,
            execution_id,
        )
        return execution_id

    def run(self, job_id, wait=False, timeout=None, poll_interval=None):
        poll_interval = poll_interval if poll_interval is not None else 5
        status = "unknown"
        exec_id = self.run_job(job_id)
        if not wait:
            return status
        pending_statuses = {"dispatching", "executing"}
        if timeout:
            start = time.monotonic()
        while True:
            status = self.get_execution_status(exec_id)
            logger.info(
                "Status: %s",
                status,
            )
            if status not in pending_statuses:
                return status
            if timeout:
                if time.monotonic() - start >= timeout:
                    raise TimeoutError(
                        f"Job {job_id} did not complete within {timeout} seconds"
                    )
            time.sleep(poll_interval)


class LoggedSession(requests.Session):
    def request(self, method, url, **kwargs):
        start = time.monotonic()
        resp = None
        try:
            resp = super().request(method, url, **kwargs)
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.debug(
                "HTTP %s %s -> %s (%.1fms)",
                method,
                resp.url,
                resp.status_code,
                elapsed_ms,
            )
            logger.debug("Headers: %s", dict(resp.headers))
            logger.debug("Body: %s", resp.text[:2000])
            return resp
        except requests.RequestException as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            status = getattr(resp, "status_code", None)
            response_text = getattr(resp, "text", None)
            response_url = getattr(resp, "url", url)
            logger.error(
                "HTTP FAIL %s %s -> %s (%.1fms) | error=%s | body=%s",
                method,
                response_url,
                status,
                elapsed_ms,
                repr(e),
                (response_text[:1000] if response_text else None),
                exc_info=True,
            )
            raise


class AuthSession(LoggedSession):
    def __init__(self, access_token):
        super().__init__()
        self.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "talend-version": TALEND_API_VERSION
            }
        )
