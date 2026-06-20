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

In this package, a “job” refers to a runnable Talend Task. Running a job creates
a corresponding Talend Execution.

----

## Installation

Install the package from [PyPI][pypi-home]:

```bash
pip install talend-task
```

## CLI

`talend_task` is a CLI for running and monitoring jobs in [Talend Cloud][talend-cloud].

After installation, the `talend_task` command is available in your shell.

Select a job interactively or pass `--job` directly.

##### CLI Options:

```
$ talend_task --help
usage: talend_task [-h] [--debug] [--wait] [--activity] [--job NAME] [--timeout SECS]
                   [--poll-interval SECS]

Talend Cloud CLI

options:
  -h, --help            show this help message and exit
  --debug               enable debug logging
  --wait                wait for job to complete and return status
  --activity            show recent runs without executing job (cannot be used with --wait)
  --job NAME            job name
  --timeout SECS        timeout (requires --wait, default: none)
  --poll-interval SECS  polling interval (requires --wait, default: 5)
```

----

## CLI Configuration

The CLI requires an Access Token and an API URL for your Talend Cloud region.

- **API URL**: Talend Cloud regional API endpoint.
- **Access Token**: Generate in
  [Talend Management Console][talend-management-console].

Configuration is provided via environment variables:

```bash
export API_URL=https://api.<region>.cloud.talend.com
export ACCESS_TOKEN=<access-token>
```

(`region` = `us`, `eu`, `us-west`, etc)

Alternatively, define them in a `.env` file in the current directory:

```
API_URL=https://api.<region>.cloud.talend.com
ACCESS_TOKEN=<access-token>
```

----

## CLI Usage Examples

#### Direct mode

Run a job by providing `--job <name>`:

```bash
talend_task --wait --job Job1
```

#### Interactive mode

Run the CLI without specifying a job to select and execute one from a menu:

```bash
talend_task --wait
```

#### Activity mode

Show recent runs for a job without executing it:

```bash
talend_task --activity --job Job1
```

----

### CLI Screenshots

##### Interactive mode

![Screenshot](https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/screenshots/screenshot-terminal-interactive-mode.png)

##### Direct mode

![Screenshot](https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/screenshots/screenshot-terminal-direct-mode.png)

----

### API Usage

Use the `TalendClient` class to interact with Talend Cloud from Python.

See the [API documentation][api-docs] for details.

##### Example

```python
from talend_task import TalendClient

api_url = "https://api.us.cloud.talend.com"
access_token = "SECRET"

with TalendClient(api_url, access_token) as client:
    job_id = client.get_job_id("Job_123")
    status = client.run(job_id, wait=True)
```

----

### Development

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

### Project Structure

```
./
├── .github/
│   └── workflows/
│       └── docs.yml
│       └── test.yml
├── src/
│   └── talend_task/
│       ├── __init__.py
│       ├── cli.py
│       └── talend_client.py
├── tests/
│   ├── test_cli.py
│   └── test_talend_client.py
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
