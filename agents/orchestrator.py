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
from agno.tools.pubmed import PubmedTools
import logging
#from agno.tools.thinking import ThinkingTools
from agno.tools.knowledge import KnowledgeTools
import os
from agno.agent import Agent
# from agno.knowledge.url import UrlKnowledge
from agno.tools.knowledge import KnowledgeTools
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.knowledge.embedder.google import GeminiEmbedder


# Constants
CURRENT_USER = "codegeek03"
CURRENT_TIME = "2025-05-09 21:01:46"  # Updated with provided time

urls = [
    "https://www.fda.gov/food/food-ingredients-packaging",
    "https://www.epa.gov/facts-and-figures-about-materials-waste-and-recycling/containers-and-packaging-product-specific",
    "https://extension.uga.edu/publications/detail.html?number=C992&title=understanding-laboratory-wastewater-tests-i-organics-bod-cod-toc-og",
    "https://businessanalytiq.com/procurementanalytics/index/ldpe-price-index/",
    "https://www.mckinsey.com/industries/packaging-and-paper/our-insights/sustainability-in-packaging-us-survey-insights",
]

from agents.context import get_content_json, fetch_url_content


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# agno_docs = UrlKnowledge(
#     urls=["https://www.researchgate.net/publication/322808541_Sustainable_Packaging","https://sustainablepackaging.org/wp-content/uploads/2019/06/Definition-of-Sustainable-Packaging.pdf",
#           "https://s3.amazonaws.com/gb.assets/SPC+DG_1-8-07_FINAL.pdf","https://sustainablepackaging.org/wp-content/uploads/2019/06/Definition-of-Sustainable-Packaging.pdf"],

#     vector_db=LanceDb(
#         uri="tmp/lancedb",
#         table_name="agno_docs",
#         search_type=SearchType.hybrid,
#         embedder=GeminiEmbedder(),
#     ),
# )

# knowledge_tools = KnowledgeTools(
#     knowledge=agno_docs,
#     think=True,   
#     search=True,  
#     analyze=True,  
#     add_few_shot=True, 
# )

class OrchestrationAgent:
    def __init__(self, current_time: str = CURRENT_TIME, current_user: str = CURRENT_USER,prop_context: Dict[str, Any] = None):
        logger.info("Initializing OrchestrationAgent")
        try:
            self.current_time = current_time
            self.user_login = current_user

            load_dotenv()
            self.api_key = os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is not set")

            self.reports_dir = "temp_KB/reports"
            os.makedirs(self.reports_dir, exist_ok=True)



            self.agent = Agent(
    model=Gemini(
        id="gemini-2.0-flash",  # Use the standard model instead of experimental
        search=True,
        grounding=True,
        temperature=0.4  # Lower temperature for more focused responses
    ),
    # context={
    #     "Research_context": get_content_json(urls), 
    #     "properties": prop_context
    # },
    description="You are an expert research analyst with exceptional analytical and investigative abilities.",
    instructions=[
        "Always begin by thoroughly searching for the most relevant and up-to-date information",
        "Provide well-structured, detailed responses with clear sections",
        "Include specific facts and details to support your answers no hallucination and no irrelevant hypothetical assumptions",
        "Abide by the context in {Research_context} for reference",
        "THINK TWICE EVERY FACT WITH RESPECT TO THE {product_name} and {properties}",
        "RELEVANCY IS KEY TO YOUR SUCCESS"
    ],
    reasoning=True,
    markdown=True,
)
            logger.info("Agent initialized successfully")

            self.calculator = CalculatorTools()
            self.newspaper = Newspaper4kTools()
            self.duckduckgo = DuckDuckGoTools()
            self.googlesearch = GoogleSearchTools()
            self.pubmed = PubmedTools()
            logger.info("All tools initialized successfully"
)
            logger.info("OrchestrationAgent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OrchestrationAgent: {str(e)}", exc_info=True)
            raise

    async def generate_executive_summary(
        self,
        product_name: str,
        k: int,
        location: str,
        material: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            mat_name = material["material_name"]
            prompt = f"""
*You are a senior sustainability consultant advising Blue Yonder’s clients on optimal packaging choices. Use ONLY real, verifiable data from authoritative sources—no hallucinations or made-up figures.  
*For each metric below, your “value” must be the exact number or range you find online.
*If values are missing for any material search for any comparable material and use that instead. 
THINK TWICE EVERY FACT WITH RESPECT TO THE {product_name} and its properties as in given instruction, for example, moisture is a big issue for packaging, so it is important to consider the moisture content of the material and its effect on the product


• Product: {product_name}  
• Material: **{mat_name}**  
• Location: **{location}**  

Perform a holistic performance analysis across five dimensions: Properties, Logistics, Cost, Sustainability, Consumer Preference.  

*** METRIC CALCULATIONS (use programmatic logic):  
1. **Carbon footprint**: Find the published CO₂ emissions in kg CO₂/kg material. Map the lowest-known footprint to 100 and highest to 0 on a 0–100 scale.  
2. **Recyclability**: Locate the official recyclability percentage; use that percent as the score.  
3. **Biodegradability**: Find the documented biodegradation time (e.g. “12 months” or “200 years”). Linearly interpolate: ≤5 days→100, ≥500 years→0.  
4. **Resource efficiency**: Lookup the energy requirement in MJ/kg. Invert and rescale linearly: lowest energy use→100, highest→0.  
5. **Toxicity**: Use measured BOD or COD mg/L. Map lowest BOD/COD→100,highest→0 and interpolate using cubic spline.  

Compute a composite (equal 20% weights) unless product- or location-specific weights are provided.

Compute a composite (equal 20% weights) unless product- or location-specific weights are provided.
Don't embed any URLs in the JSON output they should be openable.

*** REQUIRED OUTPUT (valid JSON only—no extra keys, no narrative aside from specified fields):  
```json
{{
  "material_name": "{mat_name}",
  "executive_snapshot": "<one-sentence summary of fit + a Wikipedia URL for {mat_name}>",
  "composite_score": {{
    "metrics": {{
      "carbon_footprint": {{
        "value": "<e.g. 3.7 kg CO₂/kg>",
        "score": <0–100>
      }},
      "recyclability": {{
        "value": "<e.g. 85%>",
        "score": <0–100>
      }},
      "biodegradability": {{
        "value": "< eg.12 months>",
        "score": <0–100>
      }},
      "resource_efficiency": {{
        "value": "<e.g. 2.5 MJ/kg>",
        "score": <0–100>
      }},
      "toxicity": {{
        "value": "<e.g. BOD 5 mg/L>",
        "score": <0–100>
      }}
    }},
    "composite": <0–100>
  }},
  "strengths": [
    {{
      "dimension": "<e.g. 'carbon_footprint'>",
      "insight": "<why this matters for {product_name} in {location}>"
    }}
  ],
  "trade_offs": [
    {{
      "dimension": "<weaker area>",
      "mitigation": "<how strengths compensate for this for {product_name} in {location}>"
    }}
  ],
  "supply_chain_implications": {{
    "costs": "<narrative with real market‐price citations for {mat_name} in {location} and check if it can be locally sourced>",
    "logistics": "<narrative with transport & labor cost citations in {location} for packaging with {mat_name}>",
    "regulatory": "<cite exact {location}-specific packaging regs URLs and brief summary>",
    "consumer": "<narrative of social/media perceptions regarding {mat_name} — cite URLs>"
  }},
  "consulting_recommendation": {{
    "advice": "< consulting **BUSINESS INSIGHT** narrative of using {mat_name} and how to get sustainability with consumer satisfaction + relevant article URLs>"
  }},
  "regulatory_context": "<direct quote from the most relevant {location} regulation + source URL>"
}}
```

            """

            response = await self.agent.arun(prompt)
            return self._process_response(response.content)

        except Exception as e:
                logger.error(f"Error generating executive summary: {str(e)}", exc_info=True)
                return {"error": str(e)}

    def _process_response(self, response_text: str) -> Dict[str, Any]:
        try:
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response JSON: {str(e)}")
            raise ValueError(f"Invalid JSON response: {str(e)}")

    def _save_report(self, data: Dict[str, Any], report_type: str) -> str:
        try:
            timestamp = self.current_time.replace(" ", "_").replace(":", "-")
            filename = f"{report_type}_{timestamp}.json"
            filepath = os.path.join(self.reports_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {report_type} report to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save report: {str(e)}", exc_info=True)
            raise
