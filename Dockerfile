# Use official Python image
FROM python:3.11-slim

# Set working directory
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
RUN pip install poetry
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false
RUN poetry install --no-root  

# Install Playwright dependencies and browsers
RUN playwright install --with-deps

# Copy application files
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to start the FastAPI app
CMD ["uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8000"]