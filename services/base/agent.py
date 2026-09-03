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
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from agno.agent import Agent
from agno.models.google import Gemini

from libs.shared.settings import Settings, get_settings
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


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

        # Per-run identity (live, not frozen)
        self.current_time: str = self._settings.now_utc()
        self.user_login: str = self._settings.current_user

        # Ensure reports directory exists
        self.reports_dir: str = self._settings.reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

        # Build the Agno agent
        self._agent: Agent = self._build_agent()
        logger.info("%s initialised (model=%s)", self.__class__.__name__, self._settings.gemini_model_id)

    # ── private: agent construction ───────────────────────────────────────────

    def _build_agent(self) -> Agent:
        """Construct the Agno Agent with tools from the registry."""
        tools = self._tool_registry.get_many(self.tool_names)
        return Agent(
            model=Gemini(
                id=self._settings.gemini_model_id,
                search=True,
                grounding=False,
            ),
            tools=tools,
            description=self.agent_description,
            instructions=self.agent_instructions,
            reasoning=True,
            markdown=True,
        )

    # ── protected: template methods ───────────────────────────────────────────

    def _render_prompt(self, **kwargs: Any) -> str:
        """Render the user prompt template for this service."""
        return self._prompt_loader.render(self.prompt_key, **kwargs)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Strip markdown code fences and parse JSON from the LLM response.

        Subclasses may override this for non-JSON responses.
        """
        text = response_text.strip()
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
                self.__class__.__name__, exc, response_text[:500],
            )
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    async def _call_llm(self, prompt: str) -> str:
        """Call the Agno agent and return raw response text."""
        response = await self._agent.arun(prompt)
        return response.content

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
