FROM python:3.12-slim

# Install uv binary (pin version to avoid cache invalidations from `latest` tag drift)
COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /uvx /bin/

# --- FAST FFMPEG INJECTION ---
COPY --from=mwader/static-ffmpeg:7.0 /ffmpeg /ffprobe /usr/local/bin/
# ----------------------------------------------------------------------------

WORKDIR /server

# Enable bytecode compilation and unbuffered logging
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Force uv to build the virtual environment in an isolated path
# so your local volume mounts don't destroy it.
ENV UV_PROJECT_ENVIRONMENT=/venv

# Copy dependency files first for explicit layer caching
COPY pyproject.toml uv.lock ./

# Cache mount persists uv's package downloads across build invocations,
# so even when pyproject.toml/uv.lock changes (invalidating this layer),
# already-downloaded wheels are reused instead of fetched again.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Copy all source code
COPY . .

# Update path targets to look at the isolated virtual environment location
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="/server"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]