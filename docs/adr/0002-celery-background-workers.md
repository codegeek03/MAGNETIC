# ADR 0002: Celery Background Workers for Execution Offloading

## Status
Accepted

## Context
The initial prototype executed the LangGraph state machine synchronously within the Streamlit UI thread via `asyncio.create_task()`. As analysis depth grew (involving multiple concurrent LLM calls and network requests), the Streamlit frontend would freeze or timeout, delivering a poor user experience.

## Decision
We adopted **Celery** with **Redis** as a message broker to decouple graph execution from the UI.
1. The Streamlit UI submits an analysis job via `run_analysis_workflow.delay(...)`.
2. A separate Celery worker process runs the job in its own event loop.
3. The UI polls Celery/Redis for the `task.ready()` status.
4. We integrated `AsyncPostgresSaver` into LangGraph to ensure workflow states persist durably in Postgres, allowing tasks to be safely resumed or audited later.

## Consequences
**Pros:**
- The frontend UI remains highly responsive regardless of analysis duration.
- System can scale horizontally by adding more Celery workers.
- Workflows are now durably checkpointed, enabling audit logs and session resumption.

**Cons:**
- Increases infrastructure complexity (requires running Redis, Postgres, and a Celery worker alongside the web app).
- Debugging requires correlating logs across the web app and worker processes.
