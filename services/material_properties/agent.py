"""
services/material_properties/agent.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
MaterialPropertiesService — scores packaging materials on five
mechanical and barrier properties to identify the top performers.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from libs.shared.settings import Settings
from services.base.agent import BaseAgent
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry


class MaterialPropertiesService(BaseAgent):
    """
    Analyses mechanical and barrier properties of candidate materials.

    Scores: mechanical strength, chemical resistance, thermal stability,
    barrier properties, durability — all equally weighted at 20 %.
    """

    tool_names: ClassVar[List[str]] = ["fact_broker"]
    prompt_key: ClassVar[str] = "material_properties"
    agent_description: ClassVar[str] = (
        "You are a materials scientist specialising in packaging performance "
        "characterisation and life-cycle analysis."
    )
    agent_instructions: ClassVar[List[str]] = [
        "Use realistic, published property values — no hallucination.",
        "Score all five properties for each material.",
        "Return only the top 5 materials by overall score.",
        "Keep text fields under 50 characters.",
        "Reply with VALID JSON ONLY.",
    ]

    #: Property weights used for the composite score
    PROPERTY_WEIGHTS: ClassVar[Dict[str, float]] = {
        "mechanical_strength": 0.20,
        "chemical_resistance": 0.20,
        "thermal_stability":   0.20,
        "barrier_properties":  0.20,
        "durability":          0.20,
    }

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(settings, prompt_loader, tool_registry)

    # ── public API ────────────────────────────────────────────────────────────

    async def analyze_material_properties(
        self,
        materials_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Score materials on five mechanical/barrier properties.

        Parameters
        ----------
        materials_data:
            Output from :class:`MaterialsDatabaseService`, must contain
            ``product_name``.

        Returns
        -------
        dict
            JSON with ``top_materials`` list.
        """
        try:
            product_name = materials_data.get("product_name", "")
            prompt = self._render_prompt(
                product_name=product_name,
                timestamp=self.current_time,
                user=self.user_login,
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            saved_path = self._save_report(result, "material_properties")
            result["report_path"] = saved_path
            return result
        except Exception as exc:
            return self._error_response(exc, "analyze_material_properties")
