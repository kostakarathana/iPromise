# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm@sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134 AS builder

ARG UV_VERSION=0.12.1

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock README.md ./

# --frozen installs the exact lock without resolving the development-only local
# ipromise-demo path, which is intentionally outside this build context.
RUN uv sync --frozen --no-dev --extra google --extra github --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --extra google --extra github --no-editable


FROM python:3.12-slim-bookworm@sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134 AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PORT=8080 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system --gid 10001 ipromise \
    && useradd --system --uid 10001 --gid ipromise \
      --home-dir /nonexistent --shell /usr/sbin/nologin ipromise

COPY --from=builder --chown=ipromise:ipromise /app/.venv /app/.venv

USER 10001:10001
EXPOSE 8080

CMD ["sh", "-c", "exec python -m uvicorn ipromise_agent.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
