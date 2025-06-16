FROM webrecorder/browsertrix-crawler:1.6.1 AS base

ENV RUNNING_IN_DOCKER=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/root/.local/bin:$PATH"


ARG TARGETARCH

# Installing system dependencies
RUN add-apt-repository ppa:mozillateam/ppa && \
	apt-get update && \
    apt-get install -y --no-install-recommends gcc ffmpeg fonts-noto exiftool && \
	apt-get install -y --no-install-recommends firefox-esr && \
    ln -s /usr/bin/firefox-esr /usr/bin/firefox

ARG GECKODRIVER_VERSION=0.36.0

RUN if [ $(uname -m) = "aarch64" ]; then \
        GECKODRIVER_ARCH=linux-aarch64; \
    else \
        GECKODRIVER_ARCH=linux64; \
    fi && \
    wget https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-${GECKODRIVER_ARCH}.tar.gz && \
    tar -xvzf geckodriver* -C /usr/local/bin && \
    chmod +x /usr/local/bin/geckodriver && \
    rm geckodriver-v* && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# uv and runtime
FROM base AS runtime

# Install uv
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install uv

WORKDIR /app

# Create virtual environment and copy project files
RUN uv venv
COPY pyproject.toml README.md ./

# Install dependencies only first (for better caching)
RUN uv pip install --no-deps --editable .

# Copy source code and install the package itself
COPY ./src/ .
RUN uv pip install --editable .

# Update PATH to include virtual environment binaries
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python3", "-m", "auto_archiver"]

# should be executed with 2 volumes (3 if local_storage is used)
# docker run --rm -v $PWD/secrets:/app/secrets -v $PWD/local_archive:/app/local_archive aa pipenv run python3 -m auto_archiver --config secrets/orchestration.yaml

