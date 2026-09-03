"""
services/consumer_behavior/agent.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ConsumerBehaviorService — analyses consumer behaviour patterns,
market trends, and brand alignment for packaging materials.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from libs.shared.settings import Settings
from services.base.agent import BaseAgent
from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry


class ConsumerBehaviorService(BaseAgent):
    """
    Consumer behaviour and market perception analysis service.

    Scores materials on five consumer dimensions:
      - Aesthetic Appeal   20%
      - Usability          20%
      - Perceived Value    20%
      - Eco-consciousness  20%
      - Brand Alignment    20%

    Also extracts key market trends relevant to the product category.
    """

    tool_names: ClassVar[List[str]] = ["fact_broker"]
    prompt_key: ClassVar[str] = "consumer_behavior"
    agent_description: ClassVar[str] = (
        "You are a consumer-insights analyst and behavioural economist "
        "specialising in packaging perception, sustainability trends, "
        "and brand alignment."
    )
    agent_instructions: ClassVar[List[str]] = [
        "Draw from e-commerce reviews, social media, and market research.",
        "Score all five consumer dimensions for each material.",
        "Return only the top 5 materials by overall consumer score.",
        "Keep text fields under 80 characters.",
        "Reply with VALID JSON ONLY.",
    ]

    #: Consumer dimension weights
    CONSUMER_WEIGHTS: ClassVar[Dict[str, float]] = {
        "aesthetic_appeal":  0.20,
        "usability":         0.20,
        "perceived_value":   0.20,
        "eco_consciousness": 0.20,
        "brand_alignment":   0.20,
    }

    def __init__(
        self,
        settings: Optional[Settings] = None,
        prompt_loader: Optional[PromptLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(settings, prompt_loader, tool_registry)

    # ── public API ────────────────────────────────────────────────────────────

    async def analyze_consumer_behavior(
        self,
        materials_data: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Score packaging materials on consumer behaviour dimensions.

        Parameters
        ----------
        materials_data:
            Output from :class:`MaterialsDatabaseService` with ``product_name``.
        input_data:
            Original product input dict (used for context).

        Returns
        -------
        dict
            JSON with ``top_materials`` and ``consumer_trends`` lists.
        """
        try:
            prompt = self._render_prompt(
                product_name=materials_data.get("product_name", ""),
                timestamp=self.current_time,
                user=self.user_login,
            )
            raw = await self._call_llm(prompt)
            result = self._parse_response(raw)
            saved_path = self._save_report(result, "consumer_behavior")
            result["report_path"] = saved_path
            return result
        except Exception as exc:
            return self._error_response(exc, "analyze_consumer_behavior")
