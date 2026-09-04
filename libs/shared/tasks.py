"""
libs/shared/tasks.py
~~~~~~~~~~~~~~~~~~~~
Celery task definitions and Beat schedule for the packaging platform.

Tasks:
  - run_analysis_workflow: Main analysis pipeline (enqueued by API).
  - check_compliance_updates: Ambient agent — weekly regulatory check.
  - discover_materials: Ambient agent — daily material discovery.

Progress events are published to Redis pub/sub for SSE streaming.
"""

import asyncio
import json
import logging
import os

import redis as redis_lib
import sentry_sdk
from celery import Celery
from celery.schedules import crontab
from pythonjsonlogger import jsonlogger

from main import AnalysisState, create_analysis_graph

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
    )

# ── Celery app ───────────────────────────────────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("packaging_tasks", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# ── Celery Beat schedule (Ambient Agents) ────────────────────────────────────

celery_app.conf.beat_schedule = {
    "compliance-monitor-weekly": {
        "task": "check_compliance_updates",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Monday 3 AM UTC
        "args": (),
    },
    "material-crawler-daily": {
        "task": "discover_materials",
        "schedule": crontab(hour=4, minute=0),  # Daily 4 AM UTC
        "args": (),
    },
}

# ── Redis pub/sub helper ─────────────────────────────────────────────────────

_redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)


def _publish_progress(session_id: str, node_name: str, status: str):
    """Publish a progress event to Redis pub/sub for SSE streaming."""
    try:
        event = json.dumps({
            "node": node_name,
            "status": status,
            "session_id": session_id,
        })
        _redis_client.publish(f"analysis:{session_id}", event)
    except Exception:
        pass  # Non-critical — don't fail the pipeline over a progress event


# ── Main analysis task ───────────────────────────────────────────────────────


async def _run_graph_async(
    session_id: str,
    input_data: dict,
    current_time: str,
    current_user: str,
):
    logger.info("Starting async graph execution for session %s", session_id)

    db_url = os.getenv("DATABASE_URL")

    state = AnalysisState(
        input_data=input_data,
        input_status="completed",
        error="",
        user_login=current_user,
        current_time=current_time,
    )

    config = {"configurable": {"thread_id": session_id}}

    _publish_progress(session_id, "input", "started")

    if db_url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool

        conn_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        async with AsyncConnectionPool(conn_url, kwargs={"autocommit": True}) as pool:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()
            app = create_analysis_graph(checkpointer=checkpointer)
            final_state = await app.ainvoke(state, config)
    else:
        app = create_analysis_graph()
        final_state = await app.ainvoke(state, config)

    _publish_progress(session_id, "orchestrator", "completed")
    return final_state


@celery_app.task(bind=True, name="run_analysis_workflow")
def run_analysis_workflow(
    self,
    session_id: str,
    input_data: dict,
    current_time: str,
    current_user: str,
):
    """
    Celery task that wraps the asynchronous LangGraph execution.
    It blocks inside the worker, but frees up the React UI.
    """
    logger.info("Celery task started: session_id=%s", session_id)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(
        _run_graph_async(session_id, input_data, current_time, current_user)
    )

    logger.info("Celery task finished: session_id=%s", session_id)
    return result


# ── Ambient agent tasks ──────────────────────────────────────────────────────


@celery_app.task(name="check_compliance_updates")
def check_compliance_updates():
    """Ambient agent: check for regulatory updates (weekly)."""
    from services.ambient.compliance_monitor import check_regulatory_updates

    logger.info("Ambient: starting compliance monitoring check")

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(check_regulatory_updates())
    logger.info("Ambient: compliance check result: %s", result.get("status"))
    return result


@celery_app.task(name="discover_materials")
def discover_materials():
    """Ambient agent: discover new packaging materials (daily)."""
    from services.ambient.material_crawler import discover_new_materials

    logger.info("Ambient: starting material discovery crawl")

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(discover_new_materials())
    logger.info("Ambient: material crawl result: %s", result.get("status"))
    return result
