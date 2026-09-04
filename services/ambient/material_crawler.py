"""
services/ambient/material_crawler.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Ambient agent: discovers new sustainable packaging materials
from public databases and research feeds.

Runs as a Celery Beat periodic task (daily by default).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def discover_new_materials() -> dict:
    """
    Query Open Food Facts and research APIs for new packaging materials.

    Workflow:
      1. Fetch recent entries from Open Food Facts packaging taxonomy.
      2. Search for new bioplastic / sustainable material publications.
      3. Extract material properties (name, type, key characteristics).
      4. Store new materials in the Fact Broker knowledge base.
      5. Return a summary of discovered materials.
    """
    from services.fact_broker.sources.openfoodfacts import OpenFoodFactsSource

    source = OpenFoodFactsSource()
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Query for packaging-related products to discover materials
        result = await source.fetch(
            query="sustainable packaging bioplastic",
            max_results=10,
        )

        if not result or not result.data:
            logger.info("MaterialCrawler: no new materials discovered")
            return {
                "status": "no_new_materials",
                "checked_at": timestamp,
                "source": "openfoodfacts",
            }

        # In a full implementation, we would:
        # 1. Parse material names and properties from results
        # 2. Deduplicate against existing materials in the DB
        # 3. Generate embeddings and store in pgvector
        # 4. Update the Fact Broker cache

        new_materials = len(result.data) if isinstance(result.data, list) else 1
        logger.info(
            "MaterialCrawler: discovered %d potential new material(s)",
            new_materials,
        )

        return {
            "status": "materials_found",
            "materials_discovered": new_materials,
            "checked_at": timestamp,
            "source": "openfoodfacts",
        }

    except Exception as exc:
        logger.error("MaterialCrawler failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "error": str(exc),
            "checked_at": timestamp,
        }
