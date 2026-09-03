"""
services/fact_broker/server.py
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from libs.shared.settings import get_settings
from services.fact_broker.cache import FactCache
from services.fact_broker.circuit_breaker import CircuitBreaker, CircuitOpenError
from services.fact_broker.sources.alphavantage import AlphaVantageSource
from services.fact_broker.sources.base import FactResult
from services.fact_broker.sources.brave import BraveSearchSource
from services.fact_broker.sources.eurlex import EurlexSource
from services.fact_broker.sources.openfoodfacts import OpenFoodFactsSource

logger = logging.getLogger("fact_broker")
logging.basicConfig(level=logging.INFO)

settings = get_settings()

# Initialize components
cache = FactCache()
eurlex_source = EurlexSource()
openfoodfacts_source = OpenFoodFactsSource()
alphavantage_source = AlphaVantageSource(settings.alphavantage_api_key)
brave_source = BraveSearchSource(settings.brave_api_key)

circuit_breakers = {
    "eurlex": CircuitBreaker("eurlex"),
    "openfoodfacts": CircuitBreaker("openfoodfacts"),
    "alphavantage": CircuitBreaker("alphavantage"),
    "brave": CircuitBreaker("brave")
}

# MCP Server
mcp = FastMCP("FactBroker")


async def _fetch_with_cache_and_circuit(
    tool_name: str,
    source_client: Any,
    kwargs: Dict[str, Any],
    ttl_seconds: int
) -> FactResult:
    # 1. Check cache
    cached = cache.get(tool_name, kwargs)
    if cached:
        logger.info(f"Cache hit for {tool_name}")
        return cached

    # 2. Call source through circuit breaker
    breaker = circuit_breakers[source_client.name]
    try:
        val = await breaker.call(source_client.fetch, **kwargs)
        result = FactResult(
            value=val,
            source=source_client.name,
            fetched_at=settings.now_utc(),
            confidence=source_client.confidence,
            cache_hit=False,
            ttl_seconds=ttl_seconds
        )

        # 3. Store in cache
        cache.set(tool_name, kwargs, result)
        return result
    except CircuitOpenError as exc:
        logger.warning(str(exc))
        raise
    except Exception as exc:
        logger.error(f"Error fetching from {source_client.name}: {exc}")
        raise


@mcp.tool()
async def get_regulation_text(regulation_id: str, article: str) -> dict:
    """Fetch authoritative regulation text from EUR-Lex Cellar."""
    try:
        res = await _fetch_with_cache_and_circuit(
            "get_regulation_text",
            eurlex_source,
            {"regulation_id": regulation_id, "article": article},
            ttl_seconds=30 * 24 * 3600  # 30 days
        )
        return res.to_dict()
    except Exception as e:
        # Fallback to Brave
        try:
            logger.info("Falling back to Brave Search for regulation text")
            res = await _fetch_with_cache_and_circuit(
                "search_general",
                brave_source,
                {"query": f"{regulation_id} article {article} official text"},
                ttl_seconds=48 * 3600
            )
            res.confidence = "estimated"
            return res.to_dict()
        except Exception as fallback_e:
            return {"error": f"All sources failed: {e} and {fallback_e}"}

@mcp.tool()
async def get_material_packaging_stats(product_category: str, country: str) -> dict:
    """Fetch real packaging material usage stats from Open Food Facts."""
    try:
        res = await _fetch_with_cache_and_circuit(
            "get_material_packaging_stats",
            openfoodfacts_source,
            {"product_category": product_category, "country": country},
            ttl_seconds=7 * 24 * 3600 # 7 days
        )
        return res.to_dict()
    except Exception as e:
        # Fallback to Brave
        try:
            logger.info("Falling back to Brave Search for packaging stats")
            res = await _fetch_with_cache_and_circuit(
                "search_general",
                brave_source,
                {"query": f"packaging materials used for {product_category} in {country}"},
                ttl_seconds=48 * 3600
            )
            res.confidence = "estimated"
            return res.to_dict()
        except Exception as fallback_e:
            return {"error": f"All sources failed: {e} and {fallback_e}"}

@mcp.tool()
async def get_commodity_trend(commodity: str) -> dict:
    """Fetch commodity price trend from Alpha Vantage (proxy, not exact quote)."""
    try:
        res = await _fetch_with_cache_and_circuit(
            "get_commodity_trend",
            alphavantage_source,
            {"commodity": commodity},
            ttl_seconds=24 * 3600 # 24 hours
        )
        return res.to_dict()
    except Exception as e:
        # Fallback to Brave
        try:
            logger.info("Falling back to Brave Search for commodity trend")
            res = await _fetch_with_cache_and_circuit(
                "search_general",
                brave_source,
                {"query": f"{commodity} commodity price trend"},
                ttl_seconds=48 * 3600
            )
            res.confidence = "estimated"
            return res.to_dict()
        except Exception as fallback_e:
            return {"error": f"All sources failed: {e} and {fallback_e}"}

@mcp.tool()
async def search_general(query: str) -> dict:
    """General web search via Brave Search with Gemini grounding as fallback."""
    try:
        res = await _fetch_with_cache_and_circuit(
            "search_general",
            brave_source,
            {"query": query},
            ttl_seconds=48 * 3600 # 48 hours
        )
        return res.to_dict()
    except Exception as e:
        # We can implement gemini fallback here if FACT_BROKER_GEMINI_FALLBACK=true
        if os.getenv("FACT_BROKER_GEMINI_FALLBACK", "false").lower() == "true":
            # Simple stub for gemini fallback
            return {
                "value": f"[Gemini Fallback Stub] for query: {query}",
                "source": "gemini_fallback",
                "fetched_at": settings.now_utc(),
                "confidence": "estimated",
                "cache_hit": False,
                "ttl_seconds": 48 * 3600
            }
        return {"error": f"Brave search failed and gemini fallback disabled: {e}"}


if __name__ == "__main__":
    # Typically run as stdio server if invoked directly, or could be run as HTTP/SSE
    mcp.run("stdio")
