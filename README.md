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
jobs, including ETL pipelines, workflows, and tasks.

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
$ talend_task -h
usage: talend_task [-h] [--debug] [--wait] [--job NAME] [--poll-interval SECS]

Talend Cloud CLI

options:
  -h, --help            show this help message and exit
  --debug               enable debug logging
  --wait                wait for job to complete and return status
  --job NAME            job name
  --timeout SECS        timeout (requires --wait) (default: 0)
  --poll-interval SECS  polling interval (requires --wait) (default: 5)
```

----

## Configuration

The CLI requires an Access Token and an API URL for your Talend region.

- **Access Token**: Generate it in the
  [Talend Management Console](https://help.qlik.com/talend/management-console-user-guide).
- **API URL**: Base endpoint URL for the API you will connect to.

Configuration is provided via environment variables:

```bash
export API_URL=https://api.<region>.talend.com
export ACCESS_TOKEN=<access-token>
```

Alternatively, you can define these variables in a `.env` file in the current
directory:

```
API_URL=https://api.<region>.talend.com
ACCESS_TOKEN=<access-token>
```

----

## Usage Examples

#### Direct mode

Run a specific job immediately by providing `--job <name>`:

```bash
talend_task --job Job1
```

#### Interactive mode

Run the CLI without specifying a job to select and execute one from a menu:

```bash
talend_task
```

Optionally, add the `--wait` flag in either mode to wait for the job to complete and return its final status.

```bash
talend_task --wait --job Job1
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
