FROM python:3.12-slim

# Install uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set work directory inside container
WORKDIR /server

# Enable bytecode compilation and unbuffered logging
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy dependency files first for caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Copy all source code
COPY . .

ENV PATH="/server/.venv/bin:$PATH"
ENV PYTHONPATH="/server"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
