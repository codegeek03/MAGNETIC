"""
services/sustainability/agent.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SustainabilityService — evaluates environmental impact of packaging
materials on carbon footprint, recyclability, biodegradability,
resource efficiency, and toxicity.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Type

from pydantic import BaseModel

from libs.shared.schemas.analysis import SustainabilityResult
from libs.shared.settings import Settings
from services.base.agent import BaseAgent
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry


class SustainabilityService(BaseAgent):
    """
    Environmental impact analysis service.

    Scores materials on five LCA-inspired metrics:
      - Carbon Footprint   25%
      - Recyclability      25%
      - Biodegradability   20%
      - Resource Efficiency 15%
      - Toxicity           15%
    """

    @property
    def response_model(self) -> Optional[Type[BaseModel]]:
        return SustainabilityResult

    tool_names: ClassVar[List[str]] = ["fact_broker"]
    prompt_key: ClassVar[str] = "sustainability"
    agent_description: ClassVar[str] = (
        "You are an environmental scientist and sustainability analyst "
        "specialising in life-cycle assessment (LCA) of packaging materials."
    )
    agent_instructions: ClassVar[List[str]] = [
        "Use only published, verifiable environmental data — no hallucination.",
        "Score all five metrics for each material.",
        "Return only the top 5 most environmentally friendly materials.",
        "ONLY include materials originally used for packaging.",
        "Reply with VALID JSON ONLY.",
    ]

    #: Environmental metric weights
    ENV_WEIGHTS: ClassVar[Dict[str, float]] = {
        "carbon_footprint":    0.25,
        "recyclability":       0.25,
        "biodegradability":    0.20,
        "resource_efficiency": 0.15,
        "toxicity":            0.15,
    }

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(settings, prompt_loader, tool_registry)

    # ── public API ────────────────────────────────────────────────────────────

    async def analyze_environmental_impact(
        self,
        materials_data: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Score materials on five environmental metrics.

        Parameters
        ----------
        materials_data:
            Output from :class:`MaterialsDatabaseService` with ``product_name``.
        input_data:
            Original product input dict (used for context).

        Returns
        -------
        dict
            JSON with ``top_materials`` list with ``environmental_score``.
        """
        try:
            prompt = self._render_prompt(
                product_name=materials_data.get("product_name", ""),
                timestamp=self.current_time,
                user=self.user_login,
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            saved_path = self._save_report(result, "sustainability")
            result["report_path"] = saved_path
            return result
        except Exception as exc:
            return self._error_response(exc, "analyze_environmental_impact")
