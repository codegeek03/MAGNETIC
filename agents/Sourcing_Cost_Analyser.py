from agno.agent import Agent
from agno.models.google import Gemini
from dotenv import load_dotenv
import json
import os
from typing import Dict, Any
from datetime import datetime
from agno.tools.tavily import TavilyTools
from agno.tools.calculator import CalculatorTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.tools.duckduckgo import DuckDuckGoTools

class ProductionCostAgent:
    def __init__(self, model_id: str = "gemini-2.0-flash-exp", enable_markdown: bool = True):
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        self.reports_dir = "temp_KB"
        os.makedirs(self.reports_dir, exist_ok=True)

        # Fixed user and timestamp
        self.user_login = "codegeek03"
        self.current_time = "2025-04-19 21:22:20"

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

        # Define cost components and their weights
        self.cost_components = {
            "raw_material": 0.30,    # Base material cost
            "processing": 0.25,       # Manufacturing and processing
            "tariffs": 0.15,         # Import/Export duties
            "transport": 0.15,       # Shipping and handling
            "compliance": 0.15        # Regulatory and certification costs
        }

    def _save_report_to_file(self, data: Dict[str, Any], report_type: str) -> str:
        timestamp = self.current_time.replace(" ", "_").replace(":", "-")
        filename = f"{report_type}_{timestamp}.json"
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return filepath

    async def analyze_production_costs(self, materials_data: Dict[str, Any],input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes production costs with simplified metrics and response structure.
        """
        prompt = f"""
Analyze production costs for materials used in {materials_data['product_name']} at location near {input_data['packaging_location']}.
Focus on these cost components:

1. Raw Material Cost (30%) - Base material price per unit
2. Processing Cost (25%) - Manufacturing and processing expenses
3. Tariffs & Duties (15%) - Import/export fees
4. Transport Cost (15%) - Shipping and handling expenses
5. Compliance Cost (15%) - Regulatory and certification costs

Return a JSON object with exactly this structure:
{{
  "top_materials": [
    {{
      "material_name": "<name>",
      "cost_score": <0-10>,
      "base_price": "<price in USD/kg>",
      "key_costs": {{
        "raw_material": "<brief cost note>",
        "processing": "<brief cost note>",
        "tariffs": "<brief cost note>",
        "transport": "<brief cost note>",
        "compliance": "<brief cost note>"
      }},
      "total_estimated_cost": "<USD per unit>"
    }}
  ],
  "timestamp": "{self.current_time}",
  "user": "{self.user_login}"
}}

IMPORTANT:
- Return only the top 5 most cost-effective materials
- Keep cost notes under 30 characters
- Use realistic market prices
- Include all cost components
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
            
            saved_path = self._save_report_to_file(analysis, "production_costs")
            analysis["report_path"] = saved_path
            
            return analysis

        except Exception as e:
            error_data = {
                "error": f"Production cost analysis failed: {str(e)}",
                "timestamp": self.current_time,
                "user": self.user_login
            }
            return error_data

    async def generate_cost_report(self, analysis: Dict[str, Any]) -> str:
        """
        Generates a concise production cost report.
        """
        if "error" in analysis:
            return f"Error generating report: {analysis['error']}"

        report = f"""
Production Cost Analysis
======================
Analysis Date: {analysis['timestamp']}
Generated by: {analysis['user']}

Top 5 Cost-Effective Materials:
----------------------------
"""
        
        for material in analysis['top_materials']:
            report += f"\n• {material['material_name']}"
            report += f"\n  Overall Cost Score: {material['cost_score']}/10"
            report += f"\n  Base Price: {material['base_price']}"
            report += f"\n  Estimated Total Cost: {material['total_estimated_cost']}"
            report += "\n  Cost Breakdown:"
            for cost_type, note in material['key_costs'].items():
                report += f"\n    - {cost_type.replace('_', ' ').title()}: {note}"
            report += "\n"

        return report

async def main():
    try:
        # Load materials data
        with open('temp_KB/materials_by_criteria.json', 'r') as f:
            materials_data = json.load(f)

        agent = ProductionCostAgent()
        
        print("Analyzing production costs... This may take a few moments.")
        analysis = await agent.analyze_production_costs(materials_data)
        
        report = await agent.generate_cost_report(analysis)
        print("\nProduction Cost Analysis Report:")
        print(report)
        
        print(f"\nFull report saved to: {analysis.get('report_path', 'Error: Report not saved')}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())