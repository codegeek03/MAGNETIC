"""
api/main.py
~~~~~~~~~~~
FastAPI application — REST API for the Sustainable Packaging Platform.

Features:
  - POST /api/v1/analysis      → enqueue a new analysis workflow
  - GET  /api/v1/analysis/{id} → poll task status / get result
  - GET  /api/v1/analysis/{id}/stream → SSE real-time progress stream
  - GET  /api/v1/history       → past completed analyses
  - GET  /health               → deep health check (Redis + Postgres + Celery)
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional

import redis
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from libs.shared.tasks import celery_app, run_analysis_workflow

# Configure simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sustainable Packaging API",
    version="1.0.0",
    description="Multi-Agent Orchestration Platform for Sustainable Packaging Analysis",
)

# Allow CORS for React local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client for SSE pub/sub
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_client = redis.from_url(REDIS_URL, decode_responses=True)


# ── Analysis Endpoints ───────────────────────────────────────────────────────


@app.post("/api/v1/analysis")
async def start_analysis(
    product_name: str = Form(...),
    units: int = Form(...),
    length: float = Form(...),
    width: float = Form(...),
    height: float = Form(...),
    location: str = Form(...),
    budget: float = Form(...),
    properties_weight: float = Form(...),
    logistics_weight: float = Form(...),
    cost_weight: float = Form(...),
    sustainability_weight: float = Form(...),
    consumer_weight: float = Form(...),
    requires_carbon_lca: bool = Form(False),
    requires_compliance_doc: bool = Form(False),
    bom_file: Optional[UploadFile] = File(None),
):
    """Enqueue a new packaging analysis workflow."""
    try:
        volume = length * width * height
        input_data = {
            "product_name": product_name,
            "units_per_shipment": units,
            "dimensions": {"length": length, "width": width, "height": height},
            "packaging_location": location,
            "budget_constraint": budget,
            "properties_weight": properties_weight,
            "logistics_weight": logistics_weight,
            "cost_weight": cost_weight,
            "sustainability_weight": sustainability_weight,
            "consumer_weight": consumer_weight,
            "requires_carbon_lca": requires_carbon_lca,
            "requires_compliance_doc": requires_compliance_doc,
            "bom_uploaded": bom_file is not None,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "user": "system",
                "volume": volume,
            },
        }
        import uuid
        session_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()
        current_user = "system"
        
        task = run_analysis_workflow.apply_async(
            args=[session_id, input_data, current_time, current_user],
            task_id=session_id
        )
        return {"task_id": task.id, "status": "processing"}

    except Exception as e:
        logger.error("Error starting analysis: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# Backward compatibility: keep the old /api/analysis path working
@app.post("/api/analysis")
async def start_analysis_legacy(
    product_name: str = Form(...),
    units: int = Form(...),
    length: float = Form(...),
    width: float = Form(...),
    height: float = Form(...),
    location: str = Form(...),
    budget: float = Form(...),
    properties_weight: float = Form(...),
    logistics_weight: float = Form(...),
    cost_weight: float = Form(...),
    sustainability_weight: float = Form(...),
    consumer_weight: float = Form(...),
    requires_carbon_lca: bool = Form(False),
    requires_compliance_doc: bool = Form(False),
    bom_file: Optional[UploadFile] = File(None),
):
    """Legacy endpoint — redirects to v1."""
    return await start_analysis(
        product_name=product_name,
        units=units,
        length=length,
        width=width,
        height=height,
        location=location,
        budget=budget,
        properties_weight=properties_weight,
        logistics_weight=logistics_weight,
        cost_weight=cost_weight,
        sustainability_weight=sustainability_weight,
        consumer_weight=consumer_weight,
        requires_carbon_lca=requires_carbon_lca,
        requires_compliance_doc=requires_compliance_doc,
        bom_file=bom_file,
    )


@app.get("/api/v1/analysis/{task_id}")
async def get_analysis_status(task_id: str):
    """Check the status of an analysis task."""
    task = celery_app.AsyncResult(task_id)
    if task.state == "PENDING":
        return {"status": "processing"}
    elif task.state == "SUCCESS":
        return {"status": "completed", "result": task.result}
    elif task.state == "FAILURE":
        return {"status": "failed", "error": str(task.info)}
    else:
        return {"status": "processing", "state": task.state}


# Legacy path
@app.get("/api/analysis/{task_id}")
async def get_analysis_status_legacy(task_id: str):
    """Legacy endpoint."""
    return await get_analysis_status(task_id)


# ── SSE Streaming Endpoint ───────────────────────────────────────────────────


@app.get("/api/v1/analysis/{task_id}/stream")
async def stream_analysis_progress(task_id: str):
    """
    Server-Sent Events endpoint for real-time progress streaming.

    The Celery worker publishes progress events to a Redis pub/sub channel
    named `analysis:{task_id}`. This endpoint subscribes and forwards them.
    """

    async def event_generator():
        pubsub = _redis_client.pubsub()
        channel = f"analysis:{task_id}"
        pubsub.subscribe(channel)

        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    data = message["data"]
                    yield f"data: {data}\n\n"

                    # Check if this is a terminal event
                    try:
                        parsed = json.loads(data)
                        if parsed.get("status") in ("completed", "failed"):
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Also check Celery task state as a fallback
                task = celery_app.AsyncResult(task_id)
                if task.state == "SUCCESS":
                    result_data = json.dumps({"status": "completed", "result": task.result})
                    yield f"data: {result_data}\n\n"
                    break
                elif task.state == "FAILURE":
                    error_data = json.dumps({"status": "failed", "error": str(task.info)})
                    yield f"data: {error_data}\n\n"
                    break

                await asyncio.sleep(0.5)
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Deep Health Check ────────────────────────────────────────────────────────


@app.get("/health")
def health_check():
    """
    Deep health check verifying connectivity to all infrastructure services.
    Returns HTTP 200 only if Redis AND Postgres are reachable.
    """
    checks = {}

    # Redis
    try:
        _redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Postgres
    try:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            import psycopg

            # psycopg expects postgresql:// or postgres:// not postgresql+psycopg://
            conn_url = db_url.replace("postgresql+psycopg://", "postgresql://")
            with psycopg.connect(conn_url, connect_timeout=3) as conn:
                conn.execute("SELECT 1")
            checks["postgres"] = "ok"
        else:
            checks["postgres"] = "skipped (no DATABASE_URL)"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Celery workers
    try:
        inspector = celery_app.control.inspect(timeout=2.0)
        active = inspector.active()
        if active:
            checks["celery_workers"] = f"ok ({len(active)} worker(s))"
        else:
            checks["celery_workers"] = "warning: no active workers"
    except Exception as e:
        checks["celery_workers"] = f"error: {e}"

    # Determine overall status
    has_errors = any("error" in str(v) for v in checks.values())
    status_code = 503 if has_errors else 200

    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={"status": "degraded" if has_errors else "healthy", "checks": checks},
        status_code=status_code,
    )
