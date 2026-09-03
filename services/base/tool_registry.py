"""
services/base/tool_registry.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Lazy factory and cache for Agno tool instances.

Tools are constructed once per ToolRegistry instance and returned from
cache on subsequent calls — avoiding repeated initialisation overhead.

Usage::

    registry = ToolRegistry()
    tools = registry.get_many(["tavily", "duckduckgo", "newspaper4k"])
    agent = Agent(tools=tools, ...)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Names that every service can reference
AVAILABLE_TOOLS = {
    "tavily",
    "duckduckgo",
    "newspaper4k",
    "googlesearch",
    "pubmed",
    "calculator",
    "fact_broker",
}

class ToolRegistry:
    """
    Process-scoped lazy factory for Agno tool instances.

    Pass a single shared instance into every service so tools are
    constructed exactly once per process.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        from libs.shared.settings import get_settings
        self._settings = get_settings()

    # ── public API ────────────────────────────────────────────────────────────

    def get(self, name: str) -> Any:
        """Return (cached) tool instance for *name*.

        Raises
        ------
        ValueError
            If *name* is not a recognised tool.
        """
        if name not in AVAILABLE_TOOLS:
            raise ValueError(
                f"Unknown tool '{name}'. Available: {sorted(AVAILABLE_TOOLS)}"
            )
        if name not in self._cache:
            self._cache[name] = self._build(name)
            logger.debug("ToolRegistry: built tool '%s'", name)
        return self._cache[name]

    def get_many(self, names: List[str]) -> List[Any]:
        """Return a list of tool instances for all *names* (order preserved)."""
        return [self.get(n) for n in names]

    # ── private builders ──────────────────────────────────────────────────────

    def _build(self, name: str) -> Any:  # noqa: PLR0911
        if name == "fact_broker":
            from agno.tools.mcp import MCPTools
            # Assuming stdio mode for local testing via script if no URL provided
            # Otherwise we connect via SSE (if URL is valid)
            if self._settings.fact_broker_url.startswith("http"):
                return MCPTools(
                    url=self._settings.fact_broker_url,
                    transport="sse"
                )
            else:
                return MCPTools(
                    command="python",
                    args=["-m", "services.fact_broker.server"],
                    transport="stdio"
                )

        if name == "tavily":
            from agno.tools.tavily import TavilyTools

            return TavilyTools(
                search_depth="advanced",
                max_tokens=6000,
                include_answer=True,
            )
        if name == "duckduckgo":
            from agno.tools.duckduckgo import DuckDuckGoTools

            return DuckDuckGoTools()
        if name == "newspaper4k":
            from agno.tools.newspaper4k import Newspaper4kTools

            return Newspaper4kTools()
        if name == "googlesearch":
            from agno.tools.googlesearch import GoogleSearchTools

            return GoogleSearchTools()
        if name == "pubmed":
            from agno.tools.pubmed import PubmedTools

            return PubmedTools()
        if name == "calculator":
            from agno.tools.calculator import CalculatorTools

            return CalculatorTools()
        raise ValueError(f"No builder for tool '{name}'")  # unreachable
