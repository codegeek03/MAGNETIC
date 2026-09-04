"""
services/logistics/agent.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
LogisticsService — evaluates packaging materials on transportation
durability, storage efficiency, and cost effectiveness.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Type
from pydantic import BaseModel

from libs.shared.schemas.analysis import LogisticsResult
from libs.shared.settings import Settings
from services.base.agent import BaseAgent
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry


class LogisticsService(BaseAgent):
    """
    Identifies the top 5 logistically viable packaging materials.

    Considers: transportation durability, storage efficiency, cost
    effectiveness — weighted equally.
    """

    @property
    def response_model(self) -> Optional[Type[BaseModel]]:
        return LogisticsResult

    tool_names: ClassVar[List[str]] = ["fact_broker"]
    prompt_key: ClassVar[str] = "logistics"
    agent_description: ClassVar[str] = (
        "You are a logistics and supply-chain expert specialising in packaging "
        "material transportation, storage optimisation, and cost efficiency."
    )
    agent_instructions: ClassVar[List[str]] = [
        "Search for up-to-date logistics data from authoritative sources.",
        "Focus on transportation durability, storage efficiency, and cost.",
        "Return only the top 5 materials — no extras.",
        "Keep all text fields under 50 characters.",
        "Reply with VALID JSON ONLY — no narrative outside the JSON block.",
    ]

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(settings, prompt_loader, tool_registry)

    # ── public API ────────────────────────────────────────────────────────────

    async def analyze_top_logistics_materials(
        self,
        materials_data: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Identify the 5 most logistically viable materials.

        Parameters
        ----------
        materials_data:
            Output from :class:`MaterialsDatabaseService` with ``product_name``.
        input_data:
            Original product input dict (``packaging_location``,
            ``units_per_shipment``).

        Returns
        -------
        dict
            JSON with ``top_materials`` list of logistics-scored materials.
        """
        try:
            prompt = self._render_prompt(
                product_name=materials_data.get("product_name", ""),
                packaging_location=input_data.get("packaging_location", ""),
                units_per_shipment=input_data.get("units_per_shipment", 0),
                timestamp=self.current_time,
                user=self.user_login,
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            saved_path = self._save_report(result, "logistics_top5")
            result["report_path"] = saved_path
            return result
        except Exception as exc:
            return self._error_response(exc, "analyze_top_logistics_materials")
