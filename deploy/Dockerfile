# Backend image for the local dev stack.
#
# python:3.11-slim plus the host-side tools the backend shells out to: an SSH/SCP
# client (the per-step scripts SSH into ubuntu@<node>), the docker CLI (the
# local_docker execution backend runs node containers), and git/git-lfs (the
# export step commits results to a git repo). The app itself is bind-mounted and
# pip-installed at runtime (see docker-compose.yml).
FROM python:3.11-slim

# Docker Engine 29 rejects clients older than API 1.44. Docker CLI 24 only
# supports API 1.43, so keep the backend-side CLI aligned with the development
# daemon generation used by the local_docker backend.
ARG DOCKER_CLI_VERSION=29.0.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openssh-client git git-lfs curl ca-certificates tmux \
    && curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_CLI_VERSION}.tgz" \
        | tar xz -C /usr/local/bin --strip-components=1 docker/docker \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
