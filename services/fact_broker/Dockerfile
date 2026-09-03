FROM python:3.11-slim

WORKDIR /app

COPY requirements/base.txt .
RUN pip install --no-cache-dir -r base.txt mcp httpx pyyaml anyio

COPY . .

ENV FACT_BROKER_URL="http://localhost:8800/sse"
ENV PYTHONUNBUFFERED=1

EXPOSE 8800

CMD ["python", "-m", "services.fact_broker.server"]
