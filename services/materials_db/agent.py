"""
services/materials_db/agent.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
MaterialsDatabaseService — discovers candidate packaging materials
from publicly available sustainability databases and local agriculture
waste streams.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar, Dict, List, Optional

from libs.shared.settings import Settings
from services.base.agent import BaseAgent
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry


class MaterialsDatabaseService(BaseAgent):
    """
    Finds packaging materials for each product compatibility criterion.

    Queries Tavily, DuckDuckGo, and Newspaper4k for up-to-date material
    data and local agricultural waste sourcing opportunities.
    """

    tool_names: ClassVar[List[str]] = ["fact_broker"]
    prompt_key: ClassVar[str] = "materials_db"
    agent_description: ClassVar[str] = (
        "You are a packaging sustainability specialist with deep knowledge of "
        "circular-economy materials, agricultural waste valorisation, and "
        "industry-standard sustainable packaging databases."
    )
    agent_instructions: ClassVar[List[str]] = [
        "ONLY include materials originally intended for packaging — no accessories.",
        "Materials must be scientifically accurate and currently in commercial use.",
        "Avoid redundant entries (e.g. polypropylene and PP film = same material).",
        "Include locally sourcable agricultural waste materials.",
        "Reply with VALID JSON ONLY — no comments or text outside the JSON.",
    ]

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(settings, prompt_loader, tool_registry)

    # ── public API ────────────────────────────────────────────────────────────

    async def find_materials_by_criteria(
        self,
        compatibility_analysis: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Find packaging materials for each criterion in *compatibility_analysis*.

        Parameters
        ----------
        compatibility_analysis:
            Output from :class:`ProductCompatibilityService`.
        input_data:
            Original product input dict (``packaging_location``,
            ``units_per_shipment``).

        Returns
        -------
        dict
            JSON with ``materials_by_criteria`` keyed by criterion name.
        """
        try:
            criteria = compatibility_analysis.get("criteria", {})
            product_name = compatibility_analysis.get("product_name", "")
            packaging_location = compatibility_analysis.get(
                "packaging_location",
                input_data.get("packaging_location", ""),
            )
            units_per_shipment = compatibility_analysis.get(
                "units_per_shipment",
                input_data.get("units_per_shipment", 0),
            )

            # Build the expected JSON schema so the LLM fills it exactly
            schema = {
                "materials_by_criteria": {
                    key: [{"material_name": "string", "properties": "string"}] * 5
                    for key in criteria
                },
                "analysis_timestamp": self.current_time,
                "user_login": self.user_login,
                "product_name": product_name,
                "packaging_location": packaging_location,
                "units_per_shipment": units_per_shipment,
            }

            prompt = self._render_prompt(
                product_name=product_name,
                criteria_keys=list(criteria.keys()),
                packaging_location=packaging_location,
                units_per_shipment=units_per_shipment,
                schema_json=json.dumps(schema, indent=2),
                timestamp=self.current_time,
                user=self.user_login,
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            saved_path = self._save_report(result, "materials_db")
            result["report_path"] = saved_path
            return result
        except Exception as exc:
            return self._error_response(exc, "find_materials_by_criteria")
