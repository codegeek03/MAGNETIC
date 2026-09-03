import asyncio
import os
import logging
from celery import Celery
from main import AnalysisState, create_analysis_graph

# Configure JSON logging and Sentry
from pythonjsonlogger import jsonlogger
import sentry_sdk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

if sentry_dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
    )

# Initialize Celery app
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

async def _run_graph_async(session_id: str, input_data: dict, current_time: str, current_user: str):
    logger.info(f"Starting async graph execution for session {session_id}")
    
    db_url = os.getenv("DATABASE_URL")
    
    state = AnalysisState(
        input_data=input_data,
        input_status="completed",
        error="",
        user_login=current_user,
        current_time=current_time
    )
    
    config = {"configurable": {"thread_id": session_id}}
    
    if db_url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool
        
        async with AsyncConnectionPool(db_url) as pool:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup() # Ensure tables exist
            app = create_analysis_graph(checkpointer=checkpointer)
            final_state = await app.ainvoke(state, config)
    else:
        app = create_analysis_graph()
        final_state = await app.ainvoke(state, config)
        
    return final_state

@celery_app.task(bind=True, name="run_analysis_workflow")
def run_analysis_workflow(self, session_id: str, input_data: dict, current_time: str, current_user: str):
    """
    Celery task that wraps the asynchronous LangGraph execution.
    It blocks inside the worker, but frees up the React UI.
    """
    logger.info(f"Celery task started: session_id={session_id}")
    
    # Run the asyncio event loop within the sync Celery task
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    result = loop.run_until_complete(
        _run_graph_async(session_id, input_data, current_time, current_user)
    )
    
    logger.info(f"Celery task finished: session_id={session_id}")
    return result
