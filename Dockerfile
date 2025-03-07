# Use an official Python runtime as a parent image
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory to /app
WORKDIR /app


# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    xvfb \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libgtk-3-0

# Install Poetry and project dependencies
# RUN echo "3.11.0" > .python-version
# RUN pip install uv
RUN uv python install 3.11 
COPY pyproject.toml uv.lock ./
RUN touch .python-version
RUN uv sync --frozen
RUN uv add setuptools
RUN  uv run playwright install --with-deps
# Copy the current directory contents into the container at /app
COPY . /app

# Expose port 8000
EXPOSE 8000

# Define the command to run your application
CMD ["uv","run","uvicorn", "agent.api:app", "--host" ,"0.0.0.0", "--port", "8000"]