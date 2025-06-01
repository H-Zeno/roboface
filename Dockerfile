###############################################################################
# syntax=docker/dockerfile:1  ← BuildKit syntax
###############################################################################
ARG CUDA_VERSION=12.6.0
ARG UBUNTU_VERSION=22.04

# ──────────────────────────────────────────────────────────────────────────────
# 1. CUDA runtime base image
#    (README only needs the ability to *run* code, not compile it)
# ──────────────────────────────────────────────────────────────────────────────
FROM --platform=linux/amd64 \
      nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION} AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1

# ╭───────────────────────────────────────────────────────────────╮
# │ 2. Minimal OS packages                                        │
# ╰───────────────────────────────────────────────────────────────╯
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates git python3 python3-distutils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ╭───────────────────────────────────────────────────────────────╮
# │ 3. Install uv (single static binary)                          │
# ╰───────────────────────────────────────────────────────────────╯
RUN curl -Ls \
  https://github.com/astral-sh/uv/releases/latest/download/uv-$(uname -m)-unknown-linux-musl.tar.gz \
  | tar -xz -C /usr/local/bin && chmod +x /usr/local/bin/uv

# ╭───────────────────────────────────────────────────────────────╮
# │ 4. Create non-root user – required by README best practices   │
# ╰───────────────────────────────────────────────────────────────╯
ARG USERNAME=developer
ARG UID=1000
RUN groupadd -g ${UID} ${USERNAME} && useradd -m -u ${UID} -g ${USERNAME} ${USERNAME}
USER ${USERNAME}

# uv keeps wheels here → cache this directory in CI for big speed-ups
ENV UV_CACHE_DIR=/home/${USERNAME}/.cache/uv

# ╭───────────────────────────────────────────────────────────────╮
# │ 5. Copy dependency spec only and run “uv sync --no-dev”       │
# │    Doing this in a separate layer means you seldom rebuild it │
# ╰───────────────────────────────────────────────────────────────╯
WORKDIR /workspace
COPY --chown=${USERNAME}:${USERNAME} pyproject.toml uv.lock .python-version ./

# Include the local editable resource *only* so uv can resolve it
COPY --chown=${USERNAME}:${USERNAME} SimplerEnv/ ./SimplerEnv

RUN uv sync --no-dev

# ╭───────────────────────────────────────────────────────────────╮
# │ 6. Copy the rest of the project (src, docs, …)                │
# ╰───────────────────────────────────────────────────────────────╯
COPY --chown=${USERNAME}:${USERNAME} . .

# By default uv places the venv at “.venv” in the CWD
ENV PATH="/workspace/.venv/bin:${PATH}"
ENV VIRTUAL_ENV="/workspace/.venv"

# ╭───────────────────────────────────────────────────────────────╮
# │ 7. Entrypoint – drop to an interactive shell                  │
# ╰───────────────────────────────────────────────────────────────╯
ENTRYPOINT ["/bin/bash"]