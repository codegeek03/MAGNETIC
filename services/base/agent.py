"""
services/base/agent.py
~~~~~~~~~~~~~~~~~~~~~~
Abstract base class for every service agent in the platform.

All concrete service classes inherit from BaseAgent and implement:
  - ``tool_names``   (class var) — list of tool keys from ToolRegistry
  - ``prompt_key``   (class var) — key into prompts.yaml
  - ``run(**kwargs)`` — calls _build_prompt → _call_llm → _parse_response → _save_report

The Template Method pattern means:
  * Common lifecycle (prompt build, LLM call, JSON parse, file save) lives here.
  * Service-specific logic (method signatures, schema validation) lives in subclasses.

Harness engineering features:
  * Model cascading via ModelRouter (light → heavy fallback)
  * Async timeout protection on every LLM call
  * Tenacity retry with exponential backoff on transient errors
  * Guardrail hooks (input/output validation)
  * Agentic self-reflection loop for low-confidence outputs
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC
from typing import Any, ClassVar, Dict, List, Literal, Optional, Type

from agno.agent import Agent
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from libs.shared.settings import Settings, get_settings
from services.base.model_router import ModelRouter, TaskComplexity
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

# Default timeout for a single LLM call (seconds)
_DEFAULT_LLM_TIMEOUT = 120


class BaseAgent(ABC):
    """
    Template-method abstract base for all packaging analysis service agents.

    Parameters
    ----------
    settings:
        Shared application settings. Defaults to the process singleton.
    prompt_loader:
        YAML prompt loader. Defaults to a fresh PromptLoader.
    tool_registry:
        Lazy tool factory. Defaults to a fresh ToolRegistry.
    """

    # ── class-level declarations (override in each subclass) ──────────────────

    #: Tool names this service needs (see ToolRegistry.AVAILABLE_TOOLS)
    tool_names: ClassVar[List[str]] = []

    #: Key into prompts.yaml that holds this service's templates
    prompt_key: ClassVar[str] = ""

    #: Task complexity tier — controls which model the router picks.
    #: "light" → gemini-2.0-flash, "heavy" → gemini-2.5-pro
    task_complexity: ClassVar[TaskComplexity] = "light"

    #: LLM call timeout in seconds
    llm_timeout: ClassVar[int] = _DEFAULT_LLM_TIMEOUT

    @property
    def response_model(self) -> Optional[Type[BaseModel]]:
        """Optional Pydantic model for structured output."""
        return None

    #: Agno Agent description (shown to the LLM as role context)
    agent_description: ClassVar[str] = (
        "You are an expert research analyst with exceptional analytical "
        "and investigative abilities."
    )

    #: Agno Agent instructions (shown to the LLM before every call)
    agent_instructions: ClassVar[List[str]] = [
        "Always begin by thoroughly searching for the most relevant and up-to-date information.",
        "Cross-reference sources for accuracy.",
        "Provide well-structured, comprehensive responses.",
        "Include specific facts and details to support your answers.",
        "Focus on delivering accurate, concise, and actionable insights.",
        "ONLY include materials originally used for packaging; exclude accessories.",
        "DO NOT hallucinate — if unsure, say so.",
    ]

    # ── construction ──────────────────────────────────────────────────────────

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._prompt_loader = prompt_loader or PromptLoader()
        self._tool_registry = tool_registry or ToolRegistry()
        self._model_router = ModelRouter()

        # Per-run identity (live, not frozen)
        self.current_time: str = self._settings.now_utc()
        self.user_login: str = self._settings.current_user

        # Ensure reports directory exists
        self.reports_dir: str = self._settings.reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

        # Build the Agno agent
        self._agent: Agent = self._build_agent()
        logger.info(
            "%s initialised (complexity=%s, timeout=%ds)",
            self.__class__.__name__,
            self.task_complexity,
            self.llm_timeout,
        )

    # ── private: agent construction ───────────────────────────────────────────

    def _build_agent(self) -> Agent:
        """Construct the Agno Agent with model from the router."""
        tools = self._tool_registry.get_many(self.tool_names)
        model = self._model_router.get_model(self.task_complexity)
        kwargs: Dict[str, Any] = {
            "model": model,
            "tools": tools,
            "description": self.agent_description,
            "instructions": self.agent_instructions,
            "markdown": True,
        }
        if self.response_model:
            kwargs["response_model"] = self.response_model

        return Agent(**kwargs)

    # ── protected: template methods ───────────────────────────────────────────

    def _render_prompt(self, **kwargs: Any) -> str:
        """Render the user prompt template for this service."""
        return self._prompt_loader.render(self.prompt_key, **kwargs)

    def _parse_response(self, response_content: Any) -> Dict[str, Any]:
        """
        Extract JSON from the LLM response. Uses Pydantic model_dump if a
        structured response_model was used, otherwise strips markdown code fences.
        """
        if isinstance(response_content, BaseModel):
            return response_content.model_dump()

        if not isinstance(response_content, str):
            response_content = str(response_content)

        text = response_content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as exc:
            logger.error(
                "%s: failed to parse LLM JSON response — %s\nRaw:\n%s",
                self.__class__.__name__, exc, response_content[:500],
            )
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    @retry(
        retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_llm(self, prompt: str) -> Any:
        """
        Call the Agno agent with timeout protection and retry-with-backoff.

        On transient errors (timeout, connection), retries up to 3 times
        with exponential backoff.
        """
        try:
            from libs.shared.tracing import TracingContext
            
            with TracingContext(
                agent_name=self.__class__.__name__, 
                session_id=""
            ) as trace:
                response = await asyncio.wait_for(
                    self._agent.arun(prompt),
                    timeout=self.llm_timeout,
                )
                
                output = response.content if response else ""
                
                # We can grab token counts if the model returned them
                # Agno often attaches them to response.metrics
                tokens_in = getattr(response, "metrics", {}).get("prompt_tokens", 0) if response else 0
                tokens_out = getattr(response, "metrics", {}).get("completion_tokens", 0) if response else 0
                
                trace.set_output(output, tokens_in=tokens_in, tokens_out=tokens_out)
                
            return output
        except asyncio.TimeoutError:
            logger.warning(
                "%s: LLM call timed out after %ds",
                self.__class__.__name__,
                self.llm_timeout,
            )
            raise TimeoutError(
                f"{self.__class__.__name__} LLM call exceeded {self.llm_timeout}s timeout"
            )

    async def _call_llm_with_fallback(self, prompt: str) -> Any:
        """
        Call the primary model; if it fails, fall back to a heavier model.

        This implements the model cascading pattern: try the cheap/fast model
        first, and only escalate to the expensive model on failure.
        """
        try:
            return await self._call_llm(prompt)
        except (ValueError, TimeoutError) as primary_err:
            fallback_model = self._model_router.get_fallback_model(
                self.task_complexity
            )
            if fallback_model is None:
                raise  # already at the heaviest tier

            logger.warning(
                "%s: primary model failed (%s), falling back to heavier model",
                self.__class__.__name__,
                primary_err,
            )
            # Build a temporary agent with the fallback model
            tools = self._tool_registry.get_many(self.tool_names)
            fallback_kwargs: Dict[str, Any] = {
                "model": fallback_model,
                "tools": tools,
                "description": self.agent_description,
                "instructions": self.agent_instructions,
                "markdown": True,
            }
            if self.response_model:
                fallback_kwargs["response_model"] = self.response_model

            fallback_agent = Agent(**fallback_kwargs)
            response = await asyncio.wait_for(
                fallback_agent.arun(prompt),
                timeout=self.llm_timeout * 2,  # give the big model more time
            )
            return response.content if response else ""

    def _save_report(self, data: Dict[str, Any], report_type: str) -> str:
        """Persist *data* as JSON under ``reports_dir`` and return the path."""
        timestamp = self.current_time.replace(" ", "_").replace(":", "-")
        filename = f"{report_type}_{timestamp}.json"
        filepath = os.path.join(self.reports_dir, filename)
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        logger.debug("%s: saved report → %s", self.__class__.__name__, filepath)
        return filepath

    def _error_response(self, exc: Exception, context: str = "") -> Dict[str, Any]:
        """Return a structured error dict that the graph can detect."""
        msg = f"{context}: {exc}" if context else str(exc)
        logger.error("%s error — %s", self.__class__.__name__, msg, exc_info=True)
        return {
            "error": msg,
            "timestamp": self.current_time,
            "user": self.user_login,
        }
