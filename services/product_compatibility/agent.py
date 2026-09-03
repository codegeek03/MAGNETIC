"""
services/product_compatibility/agent.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ProductCompatibilityService — analyses product characteristics
to determine packaging requirements and constraints.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from libs.shared.settings import Settings
from services.base.agent import BaseAgent
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry


class ProductCompatibilityService(BaseAgent):
    """
    Analyzes a product's packaging compatibility criteria.

    Uses Tavily + DuckDuckGo + Newspaper4k to verify product
    characteristics against real-world packaging standards.
    """

    tool_names: ClassVar[List[str]] = ["fact_broker"]
    prompt_key: ClassVar[str] = "product_compatibility"
    agent_description: ClassVar[str] = (
        "You are a product compatibility analysis engine specialising in "
        "packaging materials science and supply-chain risk assessment."
    )
    agent_instructions: ClassVar[List[str]] = [
        "Provide strict JSON responses with no commentary outside the JSON.",
        "One-word descriptions for compatibility criteria wherever possible.",
        "Never hallucinate — base answers on known product science.",
        "Always include all 10 criteria keys.",
    ]

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(settings, prompt_loader, tool_registry)

    # ── public API ────────────────────────────────────────────────────────────

    async def analyze_product_compatibility(
        self,
        product_name: str,
        product_inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyse packaging compatibility for *product_name*.

        Parameters
        ----------
        product_name:
            Human-readable product name (e.g. ``"Whey Protein Bar"``).
        product_inputs:
            Dict from :class:`~agents.detail_input.ProductInput` containing
            ``units_per_shipment``, ``dimensions``, ``packaging_location``,
            ``budget_constraint``.

        Returns
        -------
        dict
            Parsed JSON response containing ``criteria``, ``product_name``,
            ``packaging_location``, ``units_per_shipment``, ``budget_constraint``.
        """
        try:
            dims = product_inputs.get("dimensions", {})
            prompt = self._render_prompt(
                product_name=product_name,
                units_per_shipment=product_inputs.get("units_per_shipment", 0),
                dim_length=dims.get("length", 0),
                dim_width=dims.get("width", 0),
                dim_height=dims.get("height", 0),
                packaging_location=product_inputs.get("packaging_location", ""),
                budget_constraint=product_inputs.get("budget_constraint", 0.0),
                timestamp=self.current_time,
                user=self.user_login,
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            # Ensure mandatory fields are present
            result.setdefault("product_name", product_name)
            result.setdefault("packaging_location", product_inputs.get("packaging_location", ""))
            result.setdefault("units_per_shipment", product_inputs.get("units_per_shipment", 0))
            result.setdefault("budget_constraint", product_inputs.get("budget_constraint", 0.0))
            return result
        except Exception as exc:
            return self._error_response(exc, "analyze_product_compatibility")

    # ── private helpers ───────────────────────────────────────────────────────

    def _generate_analysis_prompt(self, product_name: str, product_inputs: Dict[str, Any]) -> str:
        """Legacy helper — delegates to _render_prompt for backward compat."""
        dims = product_inputs.get("dimensions", {})
        return self._render_prompt(
            product_name=product_name,
            units_per_shipment=product_inputs.get("units_per_shipment", 0),
            dim_length=dims.get("length", 0),
            dim_width=dims.get("width", 0),
            dim_height=dims.get("height", 0),
            packaging_location=product_inputs.get("packaging_location", ""),
            budget_constraint=product_inputs.get("budget_constraint", 0.0),
            timestamp=self.current_time,
            user=self.user_login,
        )
