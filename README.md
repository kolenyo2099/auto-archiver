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

### Quick Setup for macOS Slack Bot (using `uv`)

For macOS users, this setup creates a Slack bot version of Auto Archiver using `uv` (a fast Python installer and resolver).

**Prerequisites:**
- Make sure you have `uv` installed.
  - To install `uv`: `pip install uv` (or see [uv's official documentation](https://github.com/astral-sh/uv)).

**1. Installation:**

This script will create a virtual environment, install Auto Archiver with Slack bot dependencies, and set up the necessary files.

```bash
chmod +x install_macos.sh
./install_macos.sh
```

After installation, activate the environment in your terminal to run commands manually:
```bash
source .venv/bin/activate
```

**2. Setting up the Slack Bot:**

After installation, follow the setup instructions displayed by the install script:

1. **Activate the environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Create a Slack App** (if you haven't already):
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Create a new app with Socket Mode enabled
   - Add required scopes: `chat:write`, `commands`
   - Create a slash command (e.g., `/archive`)
   - Get your Bot Token (`xoxb-...`) and App Token (`xapp-...`)

3. **Configure your bot:**
   ```bash
   # Create .env file with your Slack tokens
   echo 'SLACK_BOT_TOKEN="xoxb-your-bot-token"' > .env
   echo 'SLACK_APP_TOKEN="xapp-your-app-token"' >> .env
   ```

4. **Run your Slack bot:**
   ```bash
   python slack_bot.py
   ```

5. **Test in Slack:**
   ```
   /archive https://example.com
   ```

**Optional UI Backend:**
If you want to run the optional web UI backend:
```bash
# Install UI dependencies first
uv pip install -e .[ui]
# Then run the UI
chmod +x run_macos.sh
./run_macos.sh
```

## Contributing

We welcome contributions to the Auto Archiver project! See the [Contributing Guide](https://auto-archiver.readthedocs.io/en/latest/contributing.html) for how to get involved!

