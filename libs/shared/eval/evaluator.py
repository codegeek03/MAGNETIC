"""
libs/shared/eval/evaluator.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
LLM-as-judge evaluation harness for the Multi-Agent Packaging Platform.
Scores full agent workflows against golden test cases.
"""

import json
import logging

import yaml
from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field

from main import AnalysisState, create_analysis_graph

logger = logging.getLogger(__name__)

class EvalResult(BaseModel):
    factual_accuracy_score: int = Field(ge=0, le=10)
    citation_accuracy_score: int = Field(ge=0, le=10)
    completeness_score: int = Field(ge=0, le=10)
    reasoning: str

class Evaluator:
    def __init__(self):
        self.judge = Agent(
            model=Gemini(id="gemini-2.5-flash", temperature=0.0),
            description="You are a strict LLM-as-judge evaluator scoring an agent's output.",
            instructions=[
                "Score the provided report out of 10 for Factual Accuracy, Citation Accuracy, and Completeness.",
                "Return VALID JSON ONLY matching the requested schema."
            ],
            response_model=EvalResult
        )

    def load_cases(self, file_path: str):
        with open(file_path, "r") as f:
            return yaml.safe_load(f)["cases"]

    async def run_evaluation(self, case: dict):
        logger.info(f"Running eval case: {case['id']}")

        # Build state
        state = AnalysisState(
            input_data=case["input"],
            input_status="completed",
            error="",
            user_login="eval_user",
            current_time="2026-09-04T00:00:00Z"
        )

        # Run graph
        app = create_analysis_graph()
        config = {"configurable": {"thread_id": case["id"]}}
        final_state = await app.ainvoke(state, config)

        # Assert structural expectations
        if case["expected_outcome"].get("consumer_skipped"):
            assert final_state.get("consumer_skipped") is True, "Consumer node was not skipped as expected."

        report = final_state.get("final_results", {})

        # Call LLM-as-judge
        prompt = (
            f"Evaluate this packaging report for {case['input']['product_name']}.\n"
            f"Expected Keywords: {case['expected_outcome']['preferred_material_keywords']}\n"
            f"Report:\n{json.dumps(report, indent=2)}"
        )
        eval_result = await self.judge.arun(prompt)

        logger.info(f"Eval result for {case['id']}: {eval_result}")
        return eval_result

if __name__ == "__main__":
    import asyncio
    import os

    # Simple CLI runner
    async def main():
        logging.basicConfig(level=logging.INFO)
        evaluator = Evaluator()
        cases = evaluator.load_cases(os.path.join(os.path.dirname(__file__), "eval_cases.yaml"))
        for case in cases:
            await evaluator.run_evaluation(case)

    asyncio.run(main())
