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

class MaterialPropertiesAgent:
    def __init__(self, model_id: str = "gemini-2.0-flash-exp", enable_markdown: bool = True):
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        self.reports_dir = "temp_KB"
        os.makedirs(self.reports_dir, exist_ok=True)

        # Fixed timestamp and user
        self.user_login = "codegeek03"
        self.current_time = "2025-04-19 21:27:30"

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

        # Define key properties and their weights
        self.material_properties = {
            "mechanical_strength": {
                "weight": 0.20,
                "unit": "MPa"
            },
            "chemical_resistance": {
                "weight": 0.20,
                "unit": "pH range"
            },
            "thermal_stability": {
                "weight": 0.20,
                "unit": "°C"
            },
            "barrier_properties": {
                "weight": 0.20,
                "unit": "g/(m²·day)"
            },
            "durability": {
                "weight": 0.20,
                "unit": "years"
            }
        }

    def _save_report_to_file(self, data: Dict[str, Any], report_type: str) -> str:
        timestamp = self.current_time.replace(" ", "_").replace(":", "-")
        filename = f"{report_type}_{timestamp}.json"
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return filepath

    async def analyze_material_properties(self, materials_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes material properties with simplified metrics and response structure.
        """
        prompt = f"""
Analyze the key properties of materials for {materials_data['product_name']}.
Focus on these properties:
***NOTE: ONLY INCLUDE MATERIALS ORIGINALLY USED FOR PACKAGING PURPOSES; EXCLUDE ACCESSORIES SUCH AS LABELS, PRESERVATIVES, OR PRODUCT ADDITIVES. and DONT HALLUCINATE***
1. Mechanical Strength (20%) - Tensile strength and structural integrity
2. Chemical Resistance (20%) - Resistance to various chemical environments
3. Thermal Stability (20%) - Performance across temperature range
4. Barrier Properties (20%) - Permeability to gases and moisture
5. Durability (20%) - Long-term performance and wear resistance

Return a JSON object with exactly this structure:
{{
  "top_materials": [
    {{
      "material_name": "<name>",
      "property_scores": {{
        "mechanical_strength": {{
          "value": "<numeric>",
          "unit": "MPa",
          "score": <0-10>
        }},
        "chemical_resistance": {{
          "value": "<numeric>",
          "unit": "pH range",
          "score": <0-10>
        }},
        "thermal_stability": {{
          "value": "<numeric>",
          "unit": "°C",
          "score": <0-10>
        }},
        "barrier_properties": {{
          "value": "<numeric>",
          "unit": "g/(m²·day)",
          "score": <0-10>
        }},
        "durability": {{
          "value": "<numeric>",
          "unit": "years",
          "score": <0-10>
        }}
      }},
      "overall_score": <0-10>,
      "key_strength": "<main property advantage>",
      "main_limitation": "<primary property limitation>"
    }}
  ],
  "timestamp": "{self.current_time}",
  "user": "{self.user_login}"
}}

IMPORTANT:
- Return only the top 5 materials with best overall properties
- Use realistic property values
- Keep text fields under 50 characters
- Include all properties with their units
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
            
            saved_path = self._save_report_to_file(analysis, "material_properties")
            analysis["report_path"] = saved_path
            
            return analysis

        except Exception as e:
            error_data = {
                "error": f"Properties analysis failed: {str(e)}",
                "timestamp": self.current_time,
                "user": self.user_login
            }
            return error_data

    async def generate_properties_report(self, analysis: Dict[str, Any]) -> str:
        """
        Generates a concise material properties report.
        """
        if "error" in analysis:
            return f"Error generating report: {analysis['error']}"

        report = f"""
Material Properties Analysis
==========================
Analysis Date: {analysis['timestamp']}
Generated by: {analysis['user']}

Top 5 Materials by Properties:
---------------------------
"""
        
        for material in analysis['top_materials']:
            report += f"\n• {material['material_name']}"
            report += f"\n  Overall Score: {material['overall_score']}/10"
            report += f"\n  Properties:"
            for prop_name, prop_data in material['property_scores'].items():
                report += f"\n    - {prop_name.replace('_', ' ').title()}: {prop_data['value']} {prop_data['unit']} (Score: {prop_data['score']}/10)"
            report += f"\n  Key Strength: {material['key_strength']}"
            report += f"\n  Main Limitation: {material['main_limitation']}\n"

        return report

async def main():
    try:
        # Load materials data
        with open('temp_KB/materials_by_criteria.json', 'r') as f:
            materials_data = json.load(f)

        agent = MaterialPropertiesAgent()
        
        print("Analyzing material properties... This may take a few moments.")
        analysis = await agent.analyze_material_properties(materials_data)
        
        report = await agent.generate_properties_report(analysis)
        print("\nMaterial Properties Report:")
        print(report)
        
        print(f"\nFull report saved to: {analysis.get('report_path', 'Error: Report not saved')}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())