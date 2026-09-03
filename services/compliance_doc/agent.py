import os
import logging
from typing import Dict, Any, Type
from agno.agent import Agent
from agno.models.google import Gemini
from libs.shared.schemas.analysis import ComplianceDocResult
from services.base.agent import BaseServiceAgent
from services.base.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class ComplianceDocService(BaseServiceAgent):
    def __init__(self):
        super().__init__("compliance_doc")
        
    def _create_agent(self) -> Agent:
        return Agent(
            model=Gemini(id="gemini-2.0-flash-exp"),
            description=self.prompt_config.get("description", ""),
            instructions=self.prompt_config.get("system_prompt", ""),
            response_model=ComplianceDocResult,
            markdown=True,
            show_tool_calls=True,
        )
        
    async def run_compliance_doc(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Drafting Compliance Documentation...")
        
        try:
            input_context = {
                "product_spec": state.get("input_data", {}),
                "sustainability_detail": state.get("sustainability_analysis", {}).get("detail", {})
            }
            
            prompt = (
                f"Draft the PPWR Declaration of Conformity based on the existing facts.\n"
                f"Context: {input_context}"
            )
            
            response = self.agent.run(prompt)
            result = response.content
            
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            else:
                result_dict = result
                
            return {
                "compliance_doc_analysis": result_dict,
                "compliance_doc_status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Compliance Documentation failed: {e}")
            return {
                "error": f"Compliance Documentation Agent Error: {str(e)}",
                "compliance_doc_status": "failed"
            }
