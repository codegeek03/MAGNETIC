import os
import logging
from typing import Dict, Any, Type
from agno.agent import Agent
from agno.models.google import Gemini
from libs.shared.schemas.analysis import CarbonLcaResult
from services.base.agent import BaseServiceAgent
from services.base.prompt_manager import PromptManager
from services.base.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

class CarbonLcaService(BaseServiceAgent):
    def __init__(self):
        super().__init__("carbon_lca")
        
    def _create_agent(self) -> Agent:
        return Agent(
            model=Gemini(id="gemini-2.0-flash-exp"),
            tools=[ToolRegistry.build("fact_broker")],
            description=self.prompt_config.get("description", ""),
            instructions=self.prompt_config.get("system_prompt", ""),
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
