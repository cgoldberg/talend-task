# talend-task

## CLI and Python API for running Talend Cloud jobs

- Copyright (c) 2026 [Corey Goldberg][github-profile]
- Development: [GitHub][github-repo]
- Releases: [PyPI][pypi-home]
- License: [MIT][mit-license]

----

## Status

<table>
  <tr>
    <td>Latest Version</td>
    <td>
      <a href="https://pypi.org/project/talend-task">
        <img src="https://img.shields.io/pypi/v/talend-task.svg">
      </a>
    </td>
  </tr>
  <tr>
    <td>Build (CI)</td>
    <td>
      <a href="https://github.com/cgoldberg/talend-task/actions/workflows/test.yml">
        <img src="https://github.com/cgoldberg/talend-task/actions/workflows/test.yml/badge.svg">
        <img src="https://github.com/cgoldberg/talend-task/actions/workflows/docs.yml/badge.svg">
      </a>
    </td>
  </tr>
  <tr>
    <td>Supported Python Versions</td>
    <td>
      <a href="https://pypi.org/project/talend-task">
        <img src="https://img.shields.io/pypi/pyversions/talend-task">
      </a>
    </td>
  </tr>
</table>

----

## About

The `talend-task` package provides a command-line interface and Python API
client for executing and monitoring jobs in [Talend Cloud][talend-cloud],
including ETL pipelines and other data workflows. It uses the
[Processing API][talend-processing-api] to trigger executions and monitor
their status.

The package consists of:

- command-line interface (`talend_task`)
- Python API client module (`talend_task.talend_client`) providing the
  `TalendClient` class
  - [API documentation][api-docs]

In this package, a "job" refers to a runnable Talend Task. Running a job creates
a corresponding Talend Execution.

----

## Installation

Install the package from [PyPI][pypi-home]:

```bash
pip install talend-task
```

## CLI

`talend_task` is a CLI for running and monitoring jobs in
[Talend Cloud][talend-cloud].

After installation, the `talend_task` command is available in your shell.

Select a job interactively or pass `--job` directly.

### CLI Options:

```
$ talend_task --help
usage: talend_task [-h] [--debug] [--wait] [--activity] [--job NAME] [--timeout SECS]
                   [--poll-interval SECS]

Talend Cloud CLI

options:
  -h, --help            show this help message and exit
  --debug               enable debug logging
  --wait                wait for job to complete and return status
  --activity            show recent runs without executing job (cannot use --wait)
  --job NAME            job name
  --timeout SECS        timeout (requires --wait, default: none)
  --poll-interval SECS  polling interval (requires --wait, default: 5)
```

----

### CLI Configuration

The CLI requires authentication credentials and the URL of the Talend Cloud API
endpoint for your region. These are configured using environment variables.

- **`TALEND_API_URL`**: Talend Cloud regional API endpoint

```bash
export TALEND_API_URL=https://api.<region>.cloud.talend.com
```

(`region` = `us`, `eu`, `us-west`, etc.)

#### Authentication

Talend Cloud supports two authentication methods, depending on the account
identity.

##### User Account

Regular user accounts authenticate using a **Personal Access Token (PAT)**. A
PAT represents a specific user and inherits that user's permissions. Personal
access tokens are generated in the
[Talend Management Console][talend-management-console].

- **`TALEND_ACCESS_TOKEN`**: Personal Access Token

```bash
export TALEND_ACCESS_TOKEN=<access-token>
```

##### Service Account

Service accounts authenticate using the **OAuth 2.0 Client Credentials** flow.
The **Client ID** and **Client Secret** are used to obtain a short-lived access
token from the OAuth2 token endpoint. Access tokens are automatically refreshed
before they expire.

- **`TALEND_CLIENT_ID`**: Client ID
- **`TALEND_CLIENT_SECRET`**: Client Secret

```bash
export TALEND_CLIENT_ID=<client-id>
export TALEND_CLIENT_SECRET=<client-secret>
```

#### Using a `.env` File

Instead of setting environment variables, you can define them in a `.env`
file in the current directory.

##### User account

```text
TALEND_API_URL=https://api.<region>.cloud.talend.com
TALEND_ACCESS_TOKEN=<access-token>
```

##### Service account

```text
TALEND_API_URL=https://api.<region>.cloud.talend.com
TALEND_CLIENT_ID=<client-id>
TALEND_CLIENT_SECRET=<client-secret>
```

----

### Example CLI Usage

#### Direct Mode

Run a job by providing `--job <name>`:

```bash
talend_task --wait --job Job1
```

#### Interactive Mode

Run the CLI without specifying a job to select and execute one from a menu:

```bash
talend_task --wait
```

#### Activity Mode

Show recent runs for a job without executing it:

```bash
talend_task --activity --job Job1
```

----

### CLI Screenshots

#### Interactive Mode

![Screenshot](https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/screenshots/screenshot-terminal-interactive-mode.png)

#### Direct Mode

![Screenshot](https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/screenshots/screenshot-terminal-direct-mode.png)

#### Activity Mode

![Screenshot](https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/screenshots/screenshot-terminal-activity-mode.png)

----

## Python API Client

Use the `TalendClient` and `Credential` classes to authenticate and interact
with the [Talend Cloud][talend-cloud][Processing API][talend-processing-api]
from Python.

See the [module API documentation][api-docs] for more information.

### Example Client Usage

Run a job using a Personal Aceess Token for authentication:

```python
from talend_task import StaticTokenCredential, TalendClient

api_url = "https://api.us.cloud.talend.com"
access_token = "token123"

credential = StaticTokenCredential(access_token)

with TalendClient(api_url, credential) as client:
    job_id = client.get_job_id("Job_123")
    status = client.run(job_id, wait=True)
```

Run a job using OAuth 2.0 Client Credentials flow for authentication:

```python
from talend_task import OAuthClientCredential, TalendClient

api_url = "https://api.us.cloud.talend.com"
client_id = "id123"
client_secret = "secret123"

credential = OAuthClientCredential(client_id, client_secret)

with TalendClient(api_url, credential) as client:
    job_id = client.get_job_id("Job_123")
    status = client.run(job_id, wait=True)
```
----

## Development

- Install as editable package with required development/testing
  dependencies:

    ```
    pip install --editable --group dev --group test .
    ```

- Run all tests:

    ```
    pytest
    ```

- Run linting and formatting:

    ```
    tox -e lint
    ```

- Run validation, linting, formatting, and all tests across all
  supported/installed Python environments:

    ```
    tox
    ```

## Project Structure

```
./
├── .github/
│   └── workflows/
│       ├── docs.yml
│       └── test.yml
├── src/
│   └── talend_task/
│       ├── __init__.py
│       ├── cli.py
│       └── talend_client.py
├── tests/
│   ├── test_cli.py
│   ├── test_credential.py
│   ├── test_talend_client.py
│   └── test_talend_session.py
├── pyproject.toml
└── tox.ini
```

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/talend-task
[pypi-home]: https://pypi.org/project/talend-task
[mit-license]: https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/LICENSE
[api-docs]: https://coreygoldberg.com/talend-task
[talend-cloud]: https://talend.com
[talend-management-console]: https://help.qlik.com/talend/management-console-user-guide
[talend-processing-api]: https://talend.qlik.dev/apis/processing/2021-03
