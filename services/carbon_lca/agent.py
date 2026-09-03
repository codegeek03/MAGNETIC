import logging
from typing import Any, Dict

from agno.agent import Agent
from agno.models.google import Gemini

from libs.shared.schemas.analysis import CarbonLcaResult
from libs.shared.settings import get_settings
from services.base.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

class CarbonLcaService:
    def __init__(self):
        settings = get_settings()
        self.agent = Agent(
            model=Gemini(id="gemini-2.0-flash-exp", api_key=settings.GEMINI_API_KEY),
            tools=[ToolRegistry().build("fact_broker")],
            description="You are an expert LCA analyst.",
            instructions="Calculate carbon LCA deltas.",
            response_model=CarbonLcaResult,
            markdown=True,
            show_tool_calls=True,
        )

    async def run_carbon_lca(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Running Carbon LCA analysis...")

        try:
            # Consume phase 1 outputs
            input_context = {
                "product_spec": state.get("input_data", {}),
                "sustainability_summary": state.get("sustainability_analysis", {}).get("summary", {}),
                "properties_summary": state.get("properties_analysis", {}).get("summary", {}),
                "cost_summary": state.get("cost_analysis", {}).get("summary", {})
            }

            prompt = (
                f"Analyze the carbon LCA delta for these proposed materials.\n"
                f"Context: {input_context}"
            )

            response = self.agent.run(prompt)
            result = response.content

            # Add metadata manually since we didn't use _run_analysis base method directly
            # to accommodate custom input_context.
            # Convert BaseModel to dict if needed
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            else:
                result_dict = result

            return {
                "carbon_lca_analysis": result_dict,
                "carbon_lca_status": "completed"
            }

        except Exception as e:
            logger.error(f"Carbon LCA Analysis failed: {e}")
            return {
                "error": f"Carbon LCA Analyst Error: {str(e)}",
                "carbon_lca_status": "failed"
            }
