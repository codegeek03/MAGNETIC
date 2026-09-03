FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements /app/requirements
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy source code
COPY . /app/

# The commands for running Celery or the API are in docker-compose.yml
