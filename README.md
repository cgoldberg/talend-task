# talend-task

## CLI for running Talend Cloud jobs

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
    <td>Build/Tests (CI)</td>
    <td>
      <a href="https://github.com/cgoldberg/talend-task/actions/workflows/test.yml">
        <img src="https://github.com/cgoldberg/talend-task/actions/workflows/test.yml/badge.svg">
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

`talend_task` is a Python CLI for running [Talend Cloud](https://talend.com)
jobs, including ETL pipelines, workflows, and tasks. It uses the Talend Cloud
[Processing API](https://talend.qlik.dev/apis/processing/2021-03) to trigger
job runs and monitor status.

In the CLI, a "job" refers to a runnable Talend Task. Running a job creates
a Talend Execution.

Select a job interactively, or specify one directly with `--job`.

----

## Installation

Install the package from [PyPI][pypi-home]:

```bash
pip install talend-task
```

## CLI

After installation, the `talend_task` command is available in your shell.

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

## Configuration

The CLI requires an Access Token and an API URL for your Talend Cloud region.

- **API URL**: Talend Cloud regional API endpoint.
- **Access Token**: Generate in
  [Talend Management Console](https://help.qlik.com/talend/management-console-user-guide).

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

## Usage Examples

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

### Screenshots

##### Interactive mode

![Screenshot](https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/screenshots/screenshot-terminal-interactive-mode.png)

##### Direct mode

![Screenshot](https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/screenshots/screenshot-terminal-direct-mode.png)

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
