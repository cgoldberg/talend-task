# Copyright (c) 2026 Corey Goldberg
# SPDX-License-Identifier: MIT


"""Talend Cloud Processing API client for job execution and monitoring.

This module provides a Python client for interacting with the Talend Cloud
Processing API, including job discovery, execution triggering, and execution
status polling.

Capabilities:

- Authentication using Personal Access Token or OAuth 2.0 Client Credentials flow
- Automatic HTTP session and bearer token management
- Task execution via the Talend Processing API
- Optional synchronous execution with configurable timeouts
- Polling-based execution monitoring
- Retrieval of executable jobs and metadata
- Retrieval of execution history
- Structured logging of HTTP requests, responses, and execution lifecycle events

Execution lifecycle model:

A job execution transitions through a state machine that begins at request
submission and ends in a terminal state:

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

Design notes:

- HTTP requests are executed with a shared session for connection reuse
- Responses are validated via raise_for_status() before processing
- Job metadata is cached in-memory for the lifetime of the client instance
- Polling behavior is configurable via timeout and interval parameters
- Logging is included at DEBUG/INFO/ERROR levels
"""

import logging
import time
from abc import ABC, abstractmethod

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


TALEND_API_VERSION = "2021-03"
POLL_INTERVAL = 5
HTTP_TIMEOUT = 30


class TalendClient:
    """Client for the Talend Cloud Processing API.

    This high-level client provides methods for managing and executing Talend
    Cloud jobs through the Processing API. It handles authentication, session
    management, and base URL configuration.

    Args:
    - api_url (str): Base Talend Cloud API URL
    - credential (Credential): Authentication provider used to apply
      authorization headers
    """

    def __init__(self, api_url, credential):
        self.base_url = api_url.rstrip("/") + "/processing"
        self.credential = credential
        self._session = _TalendSession(credential)
        self._jobs_cache = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _require_open(self):
        if self._session is None:
            raise RuntimeError("TalendClient is already closed")
        return self._session

    def _get(self, path):
        session = self._require_open()
        resp = session.get(
            f"{self.base_url}{path}",
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, payload):
        session = self._require_open()
        resp = session.post(
            f"{self.base_url}{path}",
            json=payload,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _jobs(self):
        """Retrieve and cache job names and executables (IDs)."""
        if self._jobs_cache is None:
            result = self._get("/executables/tasks")
            self._jobs_cache = result.get("items", [])
        return self._jobs_cache

    def close(self):
        """Close all client resources."""
        try:
            if self._session:
                self._session.close()
            self.credential.close()
        except Exception:
            logger.exception("Error closing resources")
        finally:
            self._session = None
            self._jobs_cache = None

    def get_jobs(self):
        """List available jobs and their IDs."""
        return [(item["name"], item["executable"]) for item in self._jobs()]

    def get_job_id(self, job_name):
        """Look up a job ID by name."""
        job_id = next(
            (item["executable"] for item in self._jobs() if item["name"] == job_name),
            None,
        )
        if job_id is None:
            raise ValueError(f"Unknown job: {job_name}")
        return job_id

    def run(self, job_id, wait=False, timeout=None, poll_interval=None):
        """Submit a job for execution and optionally poll until it finishes."""
        poll_interval = poll_interval if poll_interval is not None else POLL_INTERVAL
        exec_id = self.run_job(job_id)
        if not wait:
            return "unknown"
        pending_statuses = {"dispatching", "executing"}
        if timeout:
            start = time.monotonic()
        while True:
            status = self.get_execution_status(exec_id)
            logger.info("Status: %s", status)
            if status not in pending_statuses:
                return status
            if timeout:
                if time.monotonic() - start >= timeout:
                    raise TimeoutError(
                        f"Job {job_id} did not complete within {timeout} seconds"
                    )
            time.sleep(poll_interval)

    def run_job(self, job_id):
        """Submit a job for execution asynchronously."""
        result = self._post("/executions", {"executable": job_id})
        execution_id = result["executionId"]
        logger.info("Job submitted")
        logger.info("   jobId       : %s", job_id)
        logger.info("   executionId : %s", execution_id)
        return execution_id

    def get_execution_status(self, execution_id):
        """Retrieve current status of a job execution."""
        result = self._get(f"/executions/{execution_id}")
        status = result["status"]
        return status

    def get_executions(self, job_id, limit=20):
        """Retrieve recent executions for a job."""
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
            executions,
            key=lambda x: x.get("start_timestamp") or "",
            reverse=True,
        )[:limit]
        return executions


class _TalendSession(requests.Session):
    """Requests session with logging and authentication for Talend Cloud API."""

    MAX_BODY_SIZE = 2000

    def __init__(self, credential):
        super().__init__()
        self.credential = credential
        self.headers.update(
            {
                "Content-Type": "application/json",
                "talend-version": TALEND_API_VERSION,
            }
        )

    def request(self, method, url, **kwargs):
        headers = kwargs.setdefault("headers", {})
        self.credential.apply(headers)
        start = time.monotonic()
        try:
            response = super().request(method, url, **kwargs)
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log_response(method, response, elapsed_ms)
            return response
        except requests.RequestException as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log_error(method, url, e, elapsed_ms)
            raise

    def _log_response(self, method, response, elapsed_ms):
        logger.debug(
            "HTTP %s %s -> %s (%.1fms)",
            method,
            response.url,
            response.status_code,
            elapsed_ms,
        )
        logger.debug("Headers: %s", dict(response.headers))
        if response.text:
            logger.debug("Body: %s", response.text[: self.MAX_BODY_SIZE])

    def _log_error(self, method, url, exc, elapsed_ms):
        response = getattr(exc, "response", None)
        logger.error(
            "HTTP FAIL %s %s -> %s (%.1fms) | error=%s | body=%s",
            method,
            getattr(response, "url", url),
            getattr(response, "status_code", None),
            elapsed_ms,
            repr(exc),
            (
                response.text[: self.MAX_BODY_SIZE]
                if response is not None and response.text
                else None
            ),
        )


class Credential(ABC):
    """Base interface for applying authentication to HTTP requests."""

    @abstractmethod
    def apply(self, headers):
        """Apply authentication to headers."""
        raise NotImplementedError

    def close(self):
        """Close resources."""
        pass


class StaticTokenCredential(Credential):
    """Personal Access Token (PAT) credential."""

    def __init__(self, token):
        self.token = token

    def apply(self, headers):
        """Apply authentication to headers."""
        headers["Authorization"] = f"Bearer {self.token}"
        return headers


class OAuthClientCredential(Credential):
    """OAuth 2.0 Client Credentials flow with automatic token retrieval and refresh."""

    def __init__(self, api_url, client_id, client_secret, scope=None):
        self.token_url = api_url.rstrip("/") + "/security/oauth/token"
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._access_token = None
        self._expires_at = 0
        self._buffer_seconds = 30  # refresh slightly early
        self._session = requests.Session()

    def apply(self, headers):
        """Apply authentication to headers, fetching or refreshing token if needed."""
        if self._needs_refresh():
            self._refresh()
        headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def close(self):
        """Close resources."""
        self._session.close()

    def _needs_refresh(self):
        return self._access_token is None or self._is_expired()

    def _is_expired(self):
        return time.time() >= self._expires_at

    def _refresh(self):
        logger.debug("Refreshing token")
        resp = requests.post(
            self.token_url,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
            data=self._build_payload(),
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._expires_at = self._compute_expiry(data)

    def _build_payload(self) -> dict:
        payload = {"grant_type": "client_credentials"}
        if self.scope:
            payload["scope"] = self.scope
        return payload

    def _compute_expiry(self, token_response):
        expires_in = token_response.get("expires_in", 3600)
        return time.time() + expires_in - self._buffer_seconds
