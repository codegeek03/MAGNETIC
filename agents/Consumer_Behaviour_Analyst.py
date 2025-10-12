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
from agno.tools.googlesearch import GoogleSearchTools


class ConsumerBehaviorAgent:
    def __init__(self, model_id: str = "gemini-2.0-flash-exp", enable_markdown: bool = True):
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        self.reports_dir = "temp_KB"
        os.makedirs(self.reports_dir, exist_ok=True)

        # Fixed timestamp and user
        self.user_login = "codegeek03"
        self.current_time = "2025-04-19 21:34:07"

        self.agent = Agent(
    model=Gemini(
        id="gemini-2.0-flash-exp",
        search=False,  
        grounding=False  # Disable grounding to allow tools and reasoning to work
    ),
    tools=[
        TavilyTools(
            search_depth='advanced',
            max_tokens=6000,
            include_answer=True
        )
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

        # Define consumer behavior metrics and their weights
        self.behavior_metrics = {
            "aesthetic_appeal": 0.20,      # Visual attractiveness and design
            "usability": 0.20,             # Ease of use and handling
            "perceived_value": 0.20,        # Consumer perception of worth
            "eco_consciousness": 0.20,      # Environmental awareness impact
            "brand_alignment": 0.20         # Fit with brand image and values
        }

    def _save_report_to_file(self, data: Dict[str, Any], report_type: str) -> str:
        timestamp = self.current_time.replace(" ", "_").replace(":", "-")
        filename = f"{report_type}_{timestamp}.json"
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return filepath

    async def analyze_consumer_behavior(self, materials_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes consumer behavior and preferences for packaging materials.
        """
        prompt = f"""
Analyze consumer behavior patterns for packaging materials in {materials_data['product_name']} from various sites and social media comments.
Focus on these aspects:

***NOTE: ONLY INCLUDE MATERIALS ORIGINALLY USED FOR PACKAGING PURPOSES; EXCLUDE ACCESSORIES SUCH AS LABELS, PRESERVATIVES, OR PRODUCT ADDITIVES. and DONT HALLUCINATE***

1. Aesthetic Appeal (20%) - Visual attractiveness and design potential
2. Usability (20%) - Consumer handling and practical usage
3. Perceived Value (20%) - Consumer perception of quality and worth
4. Eco-consciousness (20%) - Environmental awareness and sustainability
5. Brand Alignment (20%) - Fit with brand image and market positioning

Return a JSON object with exactly this structure:
{{
  "top_materials": [
    {{
      "material_name": "<name>",
      "consumer_metrics": {{
        "aesthetic_appeal": {{
          "score": <0-10>,
          "trend_strength": "<strong|moderate|weak>",
          "key_insight": "<brief consumer insight>"
        }},
        "usability": {{
          "score": <0-10>,
          "trend_strength": "<strong|moderate|weak>",
          "key_insight": "<brief consumer insight>"
        }},
        "perceived_value": {{
          "score": <0-10>,
          "trend_strength": "<strong|moderate|weak>",
          "key_insight": "<brief consumer insight>"
        }},
        "eco_consciousness": {{
          "score": <0-10>,
          "trend_strength": "<strong|moderate|weak>",
          "key_insight": "<brief consumer insight>"
        }},
        "brand_alignment": {{
          "score": <0-10>,
          "trend_strength": "<strong|moderate|weak>",
          "key_insight": "<brief consumer insight>"
        }}
      }},
      "overall_consumer_score": <0-10>,
      "target_demographics": ["<demographic1>", "<demographic2>"],
      "market_positioning": "<brief market position statement>"
    }}
  ],
  "consumer_trends": [
    {{
      "trend_name": "<trend name>",
      "impact_level": "<high|medium|low>",
      "relevance": "<brief relevance explanation>"
    }}
  ],
  "timestamp": "{self.current_time}",
  "user": "{self.user_login}"
}}

IMPORTANT:
- Return only the top 5 materials with highest consumer appeal
- Keep insights under 50 characters
- Include realistic trend assessments
- Focus on current market trends
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
            
            saved_path = self._save_report_to_file(analysis, "consumer_behavior")
            analysis["report_path"] = saved_path
            
            return analysis

        except Exception as e:
            error_data = {
                "error": f"Consumer behavior analysis failed: {str(e)}",
                "timestamp": self.current_time,
                "user": self.user_login
            }
            return error_data

    async def generate_consumer_report(self, analysis: Dict[str, Any]) -> str:
        """
        Generates a concise consumer behavior report.
        """
        if "error" in analysis:
            return f"Error generating report: {analysis['error']}"

        report = f"""
Consumer Behavior Analysis
========================
Analysis Date: {analysis['timestamp']}
Generated by: {analysis['user']}

Top 5 Materials by Consumer Appeal:
--------------------------------
"""
        
        for material in analysis['top_materials']:
            report += f"\n• {material['material_name']}"
            report += f"\n  Overall Consumer Score: {material['overall_consumer_score']}/10"
            report += f"\n  Consumer Metrics:"
            for metric_name, metric_data in material['consumer_metrics'].items():
                report += f"\n    - {metric_name.replace('_', ' ').title()}"
                report += f"\n      Score: {metric_data['score']}/10"
                report += f"\n      Trend: {metric_data['trend_strength']}"
                report += f"\n      Insight: {metric_data['key_insight']}"
            report += f"\n  Target Demographics: {', '.join(material['target_demographics'])}"
            report += f"\n  Market Position: {material['market_positioning']}\n"

        report += "\nKey Consumer Trends:\n-------------------"
        for trend in analysis['consumer_trends']:
            report += f"\n• {trend['trend_name']}"
            report += f"\n  Impact: {trend['impact_level']}"
            report += f"\n  Relevance: {trend['relevance']}\n"

        return report

async def main():
    try:
        # Load materials data
        with open('temp_KB/materials_by_criteria.json', 'r') as f:
            materials_data = json.load(f)

        agent = ConsumerBehaviorAgent()
        
        print("Analyzing consumer behavior... This may take a few moments.")
        analysis = await agent.analyze_consumer_behavior(materials_data)
        
        report = await agent.generate_consumer_report(analysis)
        print("\nConsumer Behavior Analysis Report:")
        print(report)
        
        print(f"\nFull report saved to: {analysis.get('report_path', 'Error: Report not saved')}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())