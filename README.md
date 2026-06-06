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

## About:

`talend_task` is a Python CLI for running [Talend Cloud](https://talend.com) jobs,
including ETL pipelines, workflows, and tasks.

Jobs can be selected via the `--job` argument or chosen interactively from
a list of available jobs.

It also exposes a `TalendClient` class for use in Python applications.

----

## Installation:

#### Install from [PyPI][pypi-home]:

```
pip install talend-task
```

----

## Configuration:

You need to configure an Access Token (generated in
[Talend Management Console](https://help.qlik.com/talend/management-console-user-guide))
and the API endpoint URL you will connect to (i.e.
`https://api.<region>.talend.com`).

These are setup using the `API_URL` and `ACCESS_TOKEN` environment variables:

```
$ export API_URL=<endpoint URL>
$ export ACCESS_TOKEN=<access token>
```

You can also set this in an `.env` file in the current directory.

For example:

```
API_URL=https://api.us-west.cloud.talend.com
ACCESS_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

----

## CLI Options:

```
$ talend_task --help
usage: talend_task [-h] [--wait] [--job JOB]

options:
  -h, --help  show this help message and exit
  --wait      wait for task to complete and show status
  --job JOB   job name
```

----

## Usage Examples:

Launch the CLI to select a job to run:

```
talend_task
```

Run a job named "MyJob":

```
talend_task --job MyJob
```

Run a job named "MyJob" and wait (poll) until the job completes:

```
talend_task --wait --job MyJob
```

[github-profile]: https://github.com/cgoldberg
[github-repo]: https://github.com/cgoldberg/talend-task
[pypi-home]: https://pypi.org/project/talend-task
[mit-license]: https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/main/LICENSE
