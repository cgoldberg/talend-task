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
        self.session = AuthSession(access_token)

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
        status = "unknown"
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


class LoggedSession(requests.Session):
    def request(self, method, url, **kwargs):
        start = time.time()
        resp = None
        try:
            resp = super().request(method, url, **kwargs)
            elapsed_ms = (time.time() - start) * 1000
            logger.debug(
                "HTTP %s %s -> %s (%.1fms)",
                method,
                resp.url,
                resp.status_code,
                elapsed_ms,
            )
            logger.debug("Headers: %s", dict(resp.headers))
            logger.debug("Body: %s", resp.text[:1000])
            return resp
        except requests.RequestException as e:
            elapsed_ms = (time.time() - start) * 1000
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
            }
        )
