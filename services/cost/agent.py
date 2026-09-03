"""
services/cost/agent.py
~~~~~~~~~~~~~~~~~~~~~~
ProductionCostService — analyses total production cost for packaging
materials across five cost components.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from libs.shared.settings import Settings
from services.base.agent import BaseAgent
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry


class ProductionCostService(BaseAgent):
    """
    Analyses production costs for packaging materials.

    Cost components (fixed weights):
      - Raw Material  30%
      - Processing    25%
      - Tariffs       15%
      - Transport     15%
      - Compliance    15%
    """

    tool_names: ClassVar[List[str]] = ["fact_broker", "calculator"]
    prompt_key: ClassVar[str] = "cost"
    agent_description: ClassVar[str] = (
        "You are a procurement and costing analyst specialising in sustainable "
        "packaging materials with expertise in global commodity markets."
    )
    agent_instructions: ClassVar[List[str]] = [
        "Use realistic market prices — cite commodity databases where possible.",
        "Return only the top 5 most cost-effective materials.",
        "Keep cost notes under 30 characters.",
        "Include all five cost components for each material.",
        "Reply with VALID JSON ONLY.",
    ]

    #: Cost component weights — referenced by downstream scoring
    COST_WEIGHTS: ClassVar[Dict[str, float]] = {
        "raw_material": 0.30,
        "processing":   0.25,
        "tariffs":      0.15,
        "transport":    0.15,
        "compliance":   0.15,
    }

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(settings, prompt_loader, tool_registry)

    # ── public API ────────────────────────────────────────────────────────────

    async def analyze_production_costs(
        self,
        materials_data: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Score materials by total production cost.

        Parameters
        ----------
        materials_data:
            Output from :class:`MaterialsDatabaseService` with ``product_name``.
        input_data:
            Original product input dict (``packaging_location``,
            ``budget_constraint``).

        Returns
        -------
        dict
            JSON with ``top_materials`` list with ``cost_score`` and breakdown.
        """
        try:
            prompt = self._render_prompt(
                product_name=materials_data.get("product_name", ""),
                packaging_location=input_data.get("packaging_location", ""),
                budget_constraint=input_data.get("budget_constraint", 0.0),
                timestamp=self.current_time,
                user=self.user_login,
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            saved_path = self._save_report(result, "production_costs")
            result["report_path"] = saved_path
            return result
        except Exception as exc:
            return self._error_response(exc, "analyze_production_costs")
