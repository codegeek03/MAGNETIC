from agno.agent import Agent
from agno.models.google import Gemini
from dotenv import load_dotenv
import json
import os
from typing import Dict, Any, List
from datetime import datetime
from agno.tools.tavily import TavilyTools
from agno.tools.calculator import CalculatorTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.tools.duckduckgo import DuckDuckGoTools

class EnvironmentalImpactAgent:
    """
    Simplified agent that analyzes environmental impact of packaging materials.
    """

    def __init__(self, model_id: str = "gemini-2.0-flash-exp", enable_markdown: bool = True):
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        self.reports_dir = "temp_KB"
        os.makedirs(self.reports_dir, exist_ok=True)

        # Fixed timestamp and user
        self.user_login = "codegeek03"
        self.current_time = "2025-04-19 21:20:12"

        self.agent = Agent(
    model=Gemini(
        id="gemini-2.0-flash-exp",
        search=True,  
        grounding=False  # Disable grounding to allow tools and reasoning to work
    ),
    tools=[
        TavilyTools(
            search_depth='advanced',
            max_tokens=6000,
            include_answer=True
        ),
        DuckDuckGoTools(),
        Newspaper4kTools()
    ],
    description="You are an expert research analyst with exceptional analytical and investigative abilities.",
    instructions=[
        "Always begin by thoroughly searching for the most relevant and up-to-date information",
        "Cross-reference information between Tavily and DuckDuckGo searches for accuracy",
        "Provide well-structured, comprehensive responses with clear sections",
        "Include specific facts and details to support your answers",
        "When appropriate, organize information using bullet points or numbered lists",
        "If information seems outdated or unclear, explicitly mention this",
        "Focus on delivering accurate, concise, and actionable insights"
    ],
    reasoning=True,  # Enable reasoning 
    markdown=True,
)

        # Simplified metrics with weights
        self.environmental_metrics = {
            "carbon_footprint": 0.25,
            "recyclability": 0.25,
            "biodegradability": 0.20,
            "resource_efficiency": 0.15,
            "toxicity": 0.15
        }

    def _save_report_to_file(self, data: Dict[str, Any], report_type: str) -> str:
        """Saves analysis results to a JSON file."""
        timestamp = self.current_time.replace(" ", "_").replace(":", "-")
        filename = f"{report_type}_{timestamp}.json"
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return filepath

    async def analyze_environmental_impact(self, materials_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes environmental impact with simplified metrics and response structure.
        """
        prompt = f"""
Analyze the environmental impact of materials for {materials_data['product_name']}.
Consider these key metrics:
1. Carbon Footprint (25%) - CO2 emissions in production and disposal
2. Recyclability (25%) - Ease and efficiency of recycling
3. Biodegradability (20%) - Natural decomposition capability
4. Resource Efficiency (15%) - Natural resource consumption
5. Toxicity (15%) - Environmental hazard potential

Return a JSON object with exactly this structure:
{{
  "top_materials": [
    {{
      "material_name": "<name>",
      "environmental_score": <0-10>,
      "key_benefit": "<single main environmental advantage>",
      "primary_concern": "<main environmental challenge>"
    }}
  ],
  "timestamp": "{self.current_time}",
  "user": "{self.user_login}"
}}

IMPORTANT:
- Return only the top 5 most environmentally friendly materials
- Keep text fields under 50 characters
- Focus on practical environmental impacts
"""

        try:
            response = await self.agent.arun(prompt)
            
            response_text = response.content.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            analysis = json.loads(response_text)
            
            saved_path = self._save_report_to_file(analysis, "environmental_impact")
            analysis["report_path"] = saved_path
            
            return analysis

        except Exception as e:
            error_data = {
                "error": f"Environmental analysis failed: {str(e)}",
                "timestamp": self.current_time,
                "user": self.user_login
            }
            return error_data

    async def generate_brief_report(self, analysis: Dict[str, Any]) -> str:
        """
        Generates a concise environmental impact report.
        """
        if "error" in analysis:
            return f"Error generating report: {analysis['error']}"

        report = f"""
Environmental Impact Analysis
===========================
Analysis Date: {analysis['timestamp']}
Generated by: {analysis['user']}

Top 5 Environmentally-Friendly Materials:
--------------------------------------
"""
        
        for material in analysis['top_materials']:
            report += f"\n• {material['material_name']}"
            report += f"\n  Score: {material['environmental_score']}/10"
            report += f"\n  Key Benefit: {material['key_benefit']}"
            report += f"\n  Primary Concern: {material['primary_concern']}\n"

        return report

async def main():
    try:
        # Load materials data
        with open('temp_KB/materials_by_criteria.json', 'r') as f:
            materials_data = json.load(f)

        agent = EnvironmentalImpactAgent()
        
        print("Analyzing environmental impact... This may take a few moments.")
        analysis = await agent.analyze_environmental_impact(materials_data)
        
        report = await agent.generate_brief_report(analysis)
        print("\nEnvironmental Impact Report:")
        print(report)
        
        print(f"\nFull report saved to: {analysis.get('report_path', 'Error: Report not saved')}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())