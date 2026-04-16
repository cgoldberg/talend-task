# talend-task

## CLI for running ETL jobs (tasks) remotely via Talend Cloud API

- Copyright (c) 2026 [Corey Goldberg](https://github.com/cgoldberg)

<table>
  <tr>
    <td>Development</td>
    <td>
      <a href="https://github.com/cgoldberg/talend-task">
        GitHub
      </a>
    </td>
  </tr>
  <tr>
    <td>License</td>
    <td>
      <a href="https://raw.githubusercontent.com/cgoldberg/talend-task/refs/heads/master/LICENSE">
        MIT
      </a>
    </td>
  </tr>
  <tr>
    <td>Releases</td>
    <td>
      <a href="https://pypi.org/project/talend-task">
        PyPI
      </a>
    </td>
  </tr>
  <tr>
    <td>Supported Python Versions</td>
    <td>
      3.10+
    </td>
  </tr>
</table>

----

## About:

`talend-task` is a Python CLI tool for remotely running
[Talend](https://talend.com) ETL jobs (tasks).

You can specify a job to run by its name (using the `--job` argument)
or it will list all available jobs and let you select which one to run.

----

## Installation:

#### Install from [PyPI](https://pypi.org/project/talend-task):

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
  --job JOB   Talend ETL task name
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
