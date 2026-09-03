"""
services/orchestrator/agent.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
OrchestratorService — synthesises all upstream analysis results into
a holistic executive summary with composite scoring and consulting
recommendations, powered by Gemini with web grounding enabled.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Dict, List, Optional

from agno.agent import Agent
from agno.models.google import Gemini

from libs.shared.settings import Settings
from services.base.agent import BaseAgent
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class OrchestratorService(BaseAgent):
    """
    Executive summary and consulting recommendation service.

    Key differences from other services:
    - Runs with **grounding=True** (Gemini web-search grounding) for
      authoritative, citable data.
    - Temperature is reduced to 0.4 for more focused, factual output.
    - Uses Tavily + PubMed for additional literature search.
    """

    tool_names: ClassVar[List[str]] = ["fact_broker"]
    prompt_key: ClassVar[str] = "orchestrator"
    agent_description: ClassVar[str] = (
        "You are a senior sustainability consultant advising clients on optimal "
        "packaging choices. Use ONLY real, verifiable data — no hallucinations."
    )
    agent_instructions: ClassVar[List[str]] = [
        "THINK TWICE about every fact before including it.",
        "Use ONLY published, verifiable data — cite sources.",
        "Compute composite scores using the provided formulae.",
        "Do NOT embed raw URLs in JSON — cite as plain text.",
        "Return VALID JSON ONLY — no narrative outside the JSON block.",
    ]

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(settings, prompt_loader, tool_registry)
        # Override: orchestrator needs grounding enabled
        self._agent = self._build_grounded_agent()

    # ── private: agent construction override ─────────────────────────────────

    def _build_grounded_agent(self) -> Agent:
        """Build the grounded Gemini agent for the orchestrator."""
        tools = self._tool_registry.get_many(self.tool_names)
        return Agent(
            model=Gemini(
                id=self._settings.gemini_model_id,
                search=True,
                grounding=True,        # ← key difference
                temperature=0.4,
            ),
            tools=tools,
            description=self.agent_description,
            instructions=self.agent_instructions,
            reasoning=True,
            markdown=True,
        )

    # ── public API ────────────────────────────────────────────────────────────

    async def generate_executive_summary(
        self,
        product_name: str,
        k: int,
        location: str,
        material: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a holistic executive summary for *material*.

        Parameters
        ----------
        product_name:
            The product being packaged.
        k:
            Rank of this material in the overall shortlist.
        location:
            Packaging / distribution location.
        material:
            Dict with at least ``material_name`` key.

        Returns
        -------
        dict
            Full executive summary JSON (composite scores, strengths,
            trade-offs, supply chain implications, consulting recommendation).
        """
        try:
            mat_name = material.get("material_name", "unknown")
            prompt = self._render_prompt(
                product_name=product_name,
                material_name=mat_name,
                location=location,
                subagent_summaries=material.get("subagent_summaries", {}),
                timestamp=self.current_time,
                user=self.user_login,
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            saved_path = self._save_report(
                result, f"executive_summary_rank{k}_{mat_name.lower().replace(' ', '_')}"
            )
            result["report_path"] = saved_path
            return result
        except Exception as exc:
            return self._error_response(exc, f"generate_executive_summary(rank={k})")

    async def analyze_error(
        self,
        error_context: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Produce a root-cause analysis when the pipeline encounters an error.

        Called by the LangGraph error_handler node.
        """
        try:
            product_name = input_data.get("product_name", "unknown")
            error_msg = error_context.get("error", "Unknown error")
            prompt = (
                f"The sustainable packaging analysis pipeline for '{product_name}' "
                f"encountered an error: {error_msg}\n\n"
                "Provide a brief root cause analysis in JSON:\n"
                '{"root_cause_analysis": {"likely_cause": "...", '
                '"recommendations": ["...", "..."]}}'
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            saved_path = self._save_report(result, "error_analysis")
            result["report_path"] = saved_path
            return result
        except Exception as exc:
            return self._error_response(exc, "analyze_error")
