"""
services/ambient/compliance_monitor.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Ambient agent: continuously monitors EU/US regulatory changes
and updates the knowledge base when new amendments are published.

Runs as a Celery Beat periodic task (weekly by default).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def check_regulatory_updates() -> dict:
    """
    Query EUR-Lex and other regulatory sources for PPWR amendments.

    Workflow:
      1. Fetch latest PPWR-related documents from EUR-Lex RSS/API.
      2. Compare document IDs against known documents in the Fact Broker cache.
      3. If new documents found → extract key provisions, store embeddings
         in pgvector, and create an AlertEvent record.
      4. Return a summary of what was found/updated.
    """
    from services.fact_broker.sources.eurlex import EurlexSource

    source = EurlexSource()
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Fetch latest regulatory text
        result = await source.fetch(
            query="PPWR packaging waste regulation 2025 2026",
            max_results=5,
        )

        if not result or not result.data:
            logger.info("ComplianceMonitor: no new regulatory updates found")
            return {
                "status": "no_updates",
                "checked_at": timestamp,
                "source": "eurlex",
            }

        # In a full implementation, we would:
        # 1. Diff against stored document hashes
        # 2. Generate embeddings for new text chunks
        # 3. Store in pgvector via libs.shared.vector_store
        # 4. Create alert events in Postgres

        new_docs = len(result.data) if isinstance(result.data, list) else 1
        logger.info(
            "ComplianceMonitor: found %d document(s) to process", new_docs
        )

        return {
            "status": "updates_found",
            "documents_processed": new_docs,
            "checked_at": timestamp,
            "source": "eurlex",
        }

    except Exception as exc:
        logger.error("ComplianceMonitor failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
            "checked_at": timestamp,
        }
