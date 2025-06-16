<h1 align="center">Auto Archiver</h1>

[![Documentation Status](https://readthedocs.org/projects/auto-archiver/badge/?version=latest)](https://auto-archiver.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/auto-archiver.svg)](https://badge.fury.io/py/auto-archiver)
[![Docker Image Version (latest by date)](https://img.shields.io/docker/v/bellingcat/auto-archiver?sort=semver&logo=docker&color=#69F0AE)](https://hub.docker.com/r/bellingcat/auto-archiver)
[![Core Test Status](https://github.com/bellingcat/auto-archiver/workflows/Core%20Tests/badge.svg)](https://github.com/bellingcat/auto-archiver/actions/workflows/tests-core.yaml)
<!-- [![Download Test Status](https://github.com/bellingcat/auto-archiver/workflows/Download%20Tests/badge.svg)](https://github.com/bellingcat/auto-archiver/actions/workflows/tests-download.yaml) -->

<!-- ![Docker Pulls](https://img.shields.io/docker/pulls/bellingcat/auto-archiver) -->
<!-- [![PyPI download month](https://img.shields.io/pypi/dm/auto-archiver.svg)](https://pypi.python.org/pypi/auto-archiver/) -->



Auto Archiver is a Python tool to automatically archive content on the web in a secure and verifiable way. It takes URLs from different sources (e.g. a CSV file, Google Sheets, command line etc.) and archives the content of each one. It can archive social media posts, videos, images and webpages. Content can be enriched, then saved either locally or remotely (S3 bucket, Google Drive). The status of the archiving process can be appended to a CSV report, or if using Google Sheets – back to the original sheet.

<div class="hidden_rtd">
  
**[See the Auto Archiver documentation for more information.](https://auto-archiver.readthedocs.io/en/latest/)**

</div>

Read the [article about Auto Archiver on bellingcat.com](https://www.bellingcat.com/resources/2022/09/22/preserve-vital-online-content-with-bellingcats-auto-archiver-tool/).


## Installation

View the [Installation Guide](https://auto-archiver.readthedocs.io/en/latest/installation/installation.html) for full instructions

**Advanced:**

To get started quickly using Docker:

`docker pull bellingcat/auto-archiver && docker run -it --rm -v secrets:/app/secrets bellingcat/auto-archiver --config secrets/orchestration.yaml`

Or pip:

`pip install auto-archiver && auto-archiver --help`

### Quick Setup for macOS (using `uv`)

For macOS users, convenience scripts are provided to set up the environment using `uv` (a fast Python installer and resolver) and run the application.

**Prerequisites:**
- Make sure you have `uv` and `Poetry` installed.
  - To install `uv`: `pip install uv` (or see [uv's official documentation](https://github.com/astral-sh/uv)).
  - To install `Poetry`: See [Poetry's official documentation](https://python-poetry.org/docs/#installation).

**1. Installation:**

This script will create a virtual environment named `.venv` in the project root, export dependencies from `pyproject.toml` (using Poetry), and install them into the virtual environment using `uv`.

```bash
chmod +x install_macos.sh
./install_macos.sh
```

After installation, activate the environment in your terminal to run commands manually:
```bash
source .venv/bin/activate
```

**2. Running the Application:**

This script activates the virtual environment and starts the Extractor UI backend. It also provides instructions for running the main `auto_archiver` CLI commands.

```bash
chmod +x run_macos.sh
./run_macos.sh
```

- The Extractor UI backend will typically be available at `http://localhost:5001`.
- Follow the on-screen instructions to run `auto_archiver` commands (like `orchestrate` or `feed`) in a new terminal, after activating the `.venv` environment there as well.
- Press `Ctrl+C` in the terminal where `run_macos.sh` is running to stop the UI backend.

## Contributing

We welcome contributions to the Auto Archiver project! See the [Contributing Guide](https://auto-archiver.readthedocs.io/en/latest/contributing.html) for how to get involved!

