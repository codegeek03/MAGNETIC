import logging
from typing import Any, Dict

from agno.agent import Agent
from agno.models.google import Gemini

from libs.shared.schemas.analysis import ComplianceDocResult
from libs.shared.settings import get_settings

logger = logging.getLogger(__name__)

class ComplianceDocService:
    def __init__(self):
        settings = get_settings()
        self.agent = Agent(
            model=Gemini(id="gemini-2.0-flash-exp", api_key=settings.GEMINI_API_KEY),
            description="You are a regulatory compliance analyst.",
            instructions="Draft PPWR documents.",
            response_model=ComplianceDocResult,
            markdown=True,
            show_tool_calls=False,
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
