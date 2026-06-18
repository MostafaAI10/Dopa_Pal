FROM python:3.12-slim

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set work directory inside container
WORKDIR /app

# Enable bytecode compilation and unbuffered logging
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy project definitions directly from the root context
COPY pyproject.toml uv.lock* ./

# Install project dependencies
RUN uv sync --frozen

# Copy the rest of the application files from root
COPY . .

# Set up the execution PATH wrappers
ENV PATH="/app/.venv/bin:$PATH"

# Point Python path directly to the nested server module folder
ENV PYTHONPATH="/app/server"

EXPOSE 8000

# Run uvicorn targeting the server directory layout module
CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8000"]