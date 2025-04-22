ARG VARIANT="3.11"
FROM python:${VARIANT}-slim

# Install required system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    curl \
    direnv \
    jq \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="/root/.local/bin:$PATH" && \
    echo 'export PATH="/root/.local/bin:$PATH"' >> /etc/profile && \
    echo 'export PATH="/root/.local/bin:$PATH"' >> /etc/bash.bashrc && \
    ln -sf /root/.local/bin/uv /usr/local/bin/uv && \
    ln -sf /root/.local/bin/uvx /usr/local/bin/uvx && \
    uv --version  # Verify installation

# Install common global dev tools with UV (with --system flag)
RUN uv pip install --system black ruff mypy pytest pytest-cov pre-commit

COPY requirements.txt .

# Install additional packages (with --system flag)
RUN uv pip install --system --upgrade pip setuptools wheel \
&& uv pip install --system --upgrade pipenv \
    && uv pip install --system -r ./requirements.txt

# If requirements.txt exists, install from it
# Note: You might need to adjust this if requirements.txt doesn't exist yet
RUN mkdir -p /workspaces
WORKDIR /workspaces