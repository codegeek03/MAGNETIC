"""
libs/shared/tracing.py
~~~~~~~~~~~~~~~~~~~~~~
Optional Langfuse integration for LLM observability and cost tracking.

If LANGFUSE_PUBLIC_KEY is set, all LLM calls are instrumented with trace
spans capturing: input/output tokens, latency, model used, agent name,
session ID, and estimated cost.

If Langfuse is not configured, the module provides no-op wrappers so
the rest of the codebase doesn't need conditional imports.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_langfuse_client = None
_langfuse_enabled = False


def _init_langfuse():
    """Lazily initialize Langfuse client if credentials are available."""
    global _langfuse_client, _langfuse_enabled

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if public_key and secret_key:
        try:
            from langfuse import Langfuse

            _langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            _langfuse_enabled = True
            logger.info("Langfuse tracing enabled (host=%s)", host)
        except ImportError:
            logger.warning(
                "LANGFUSE keys set but 'langfuse' package not installed. "
                "Install with: pip install langfuse"
            )
        except Exception as exc:
            logger.warning("Failed to initialize Langfuse: %s", exc)
    else:
        logger.debug("Langfuse tracing disabled (no LANGFUSE_PUBLIC_KEY)")


# Initialize on import
_init_langfuse()


class TracingContext:
    """
    Context manager for tracing an LLM call with Langfuse.

    Usage::

        with TracingContext(agent_name="MaterialProperties", session_id="abc") as ctx:
            result = await agent.arun(prompt)
            ctx.set_output(result)
    """

    def __init__(
        self,
        agent_name: str,
        session_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.agent_name = agent_name
        self.session_id = session_id
        self.metadata = metadata or {}
        self._trace = None
        self._span = None
        self._start_time = 0.0

    def __enter__(self):
        self._start_time = time.time()

        if _langfuse_enabled and _langfuse_client:
            try:
                self._trace = _langfuse_client.trace(
                    name=f"agent:{self.agent_name}",
                    session_id=self.session_id or None,
                    metadata=self.metadata,
                )
                self._span = self._trace.span(
                    name="llm_call",
                    metadata={"agent": self.agent_name},
                )
            except Exception as exc:
                logger.debug("Langfuse trace creation failed: %s", exc)

        return self

    def set_output(self, output: Any, tokens_in: int = 0, tokens_out: int = 0):
        """Record the output and token usage."""
        if self._span:
            try:
                self._span.end(
                    output=str(output)[:2000],  # truncate for storage
                    metadata={
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "latency_ms": int((time.time() - self._start_time) * 1000),
                    },
                )
            except Exception as exc:
                logger.debug("Langfuse span end failed: %s", exc)

    def set_error(self, error: Exception):
        """Record an error on the trace."""
        if self._span:
            try:
                self._span.end(
                    level="ERROR",
                    status_message=str(error),
                )
            except Exception as exc:
                logger.debug("Langfuse error recording failed: %s", exc)

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency_ms = int((time.time() - self._start_time) * 1000)

        if exc_val and self._span:
            self.set_error(exc_val)

        # Always log locally regardless of Langfuse
        logger.info(
            "LLM call: agent=%s session=%s latency=%dms",
            self.agent_name,
            self.session_id,
            latency_ms,
        )

        if _langfuse_enabled and _langfuse_client:
            try:
                _langfuse_client.flush()
            except Exception:
                pass

        return False  # don't suppress exceptions
