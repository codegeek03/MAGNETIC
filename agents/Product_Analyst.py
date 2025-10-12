import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from agno.agent import Agent
from agno.models.google import Gemini
from dotenv import load_dotenv
import asyncio
from agno.tools.tavily import TavilyTools
from agno.tools.calculator import CalculatorTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.tools.duckduckgo import DuckDuckGoTools

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductCompatibilityAgent:
    """
    An agent that evaluates product compatibility based on specific criteria and 
    integrates with the packaging analysis orchestrator.
    """

    def __init__(self, model_id: str = "gemini-2.0-flash-exp", enable_markdown: bool = True):
        """
        Initialize the ProductCompatibilityAgent with enhanced error handling and logging.

        Args:
            model_id: The ID of the Gemini model to use
            enable_markdown: Whether to enable markdown output
        """
        logger.info("Initializing ProductCompatibilityAgent")
        try:
            # Load environment variables
            load_dotenv()

            # Get API key from environment variables
            self.api_key = os.getenv('GOOGLE_API_KEY')
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is not set")

            # Create temp_KB directory if it doesn't exist
            self.temp_dir = "temp_KB"
            os.makedirs(self.temp_dir, exist_ok=True)

            # Store user information and timestamp
            self.user_login = "codegeek03"  # Hardcoded as per requirements
            self.current_timestamp = "2025-05-08 20:00:32"  # Hardcoded as per requirements

            # Initialize the agent with the Gemini model
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

            logger.info("ProductCompatibilityAgent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ProductCompatibilityAgent: {str(e)}", exc_info=True)
            raise

    def _normalize_scores(self, criteria: Dict[str, Any]) -> Dict[str, float]:
        """
        Normalize compatibility scores to a 0-100 scale for the orchestrator.

        Args:
            criteria: Raw criteria data from analysis

        Returns:
            Dictionary of normalized scores
        """
        try:
            # Define scoring weights for different aspects
            weights = {
                "physical_form": 1.0,
                "fragility": 0.9,
                "shelf_life": 0.8,
                "chemical_properties": 1.0,
                "hygiene_sensitivity": 0.9,
                "temperature_sensitivity": 0.8,
                "volatility_or_hazard_risk": 1.0,
                "visibility_and_display": 0.7,
                "quantity_and_dosage": 0.8,
                "value_and_theft_sensitivity": 0.9
            }

            scores = {}
            for criterion, details in criteria.items():
                # Base score calculation (0-100)
                base_score = 100
                
                # Reduce score based on concerns
                if details.get('concerns') and details['concerns'].lower() != 'none':
                    base_score -= 20  # Penalty for having concerns
                
                # Apply criterion-specific weight
                weighted_score = base_score * weights.get(criterion, 1.0)
                
                # Ensure score is within 0-100 range
                scores[criterion] = max(0, min(100, weighted_score))

            return scores

        except Exception as e:
            logger.error(f"Error normalizing scores: {str(e)}", exc_info=True)
            return {}

    async def analyze_product_compatibility(self, product_name: str, product_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze product compatibility with enhanced error handling and scoring.

        Args:
            product_name: Name of the product to analyze
            product_inputs: Dictionary containing product-specific inputs

        Returns:
            Dictionary containing compatibility analysis, concerns, and normalized scores
        """
        logger.info(f"Starting compatibility analysis for product: {product_name}")
        try:
            # Generate and execute prompt
            prompt = self._generate_analysis_prompt(product_name, product_inputs)
            response = await self.agent.arun(prompt)
            
            # Process response
            analysis = self._process_response(response.content)
            
            # Add normalized scores for orchestrator
            if 'criteria' in analysis:
                analysis['scores'] = self._normalize_scores(analysis['criteria'])
            
            # Add metadata
            analysis.update({
                'product_name': product_name,
                'packaging_location': product_inputs.get('packaging_location', 'Unknown'),
                'budget_constraint': product_inputs.get('budget_constraint', 0),
                'units_per_shipment': product_inputs.get('units_per_shipment', 0),
                'analysis_timestamp': self.current_timestamp,
                'user_login': self.user_login,
                'status': 'completed',
                'saved_path': self._save_json_to_temp(analysis, product_name)
            })

            logger.info(f"Successfully completed analysis for {product_name}")
            return analysis

        except Exception as e:
            error_msg = f"Analysis failed for {product_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "error": error_msg,
                "status": "failed",
                "product_name": product_name,
                "analysis_timestamp": self.current_timestamp,
                "user_login": self.user_login
            }

    def _generate_analysis_prompt(self, product_name: str, product_inputs: Dict[str, Any]) -> str:
        """Generate the analysis prompt with proper formatting"""
        return f"""
You are a product compatibility analysis engine.

Analyze the product "{product_name}" with these specifications:
- Units per Shipment: {product_inputs.get('units_per_shipment')}
- Dimensions: L={product_inputs.get('dimensions', {}).get('length', 0)}cm, 
              W={product_inputs.get('dimensions', {}).get('width', 0)}cm, 
              H={product_inputs.get('dimensions', {}).get('height', 0)}cm
- Location: {product_inputs.get('packaging_location')}
- Budget: {product_inputs.get('budget_constraint')} units

Provide a strict JSON response with one-word descriptions:
{{
    "criteria": {{
        "physical_form": {{"explanation": "solid", "concerns": "fragile"}},
        "fragility": {{"explanation": "sturdy", "concerns": "breakable"}},
        "shelf_life": {{"explanation": "long", "concerns": "moisture"}},
        "chemical_properties": {{"explanation": "stable", "concerns": "reactive"}},
        "hygiene_sensitivity": {{"explanation": "clean", "concerns": "contamination"}},
        "temperature_sensitivity": {{"explanation": "stable", "concerns": "melting"}},
        "volatility_or_hazard_risk": {{"explanation": "safe", "concerns": "none"}},
        "visibility_and_display": {{"explanation": "clear", "concerns": "scratches"}},
        "quantity_and_dosage": {{"explanation": "bulk", "concerns": "overflow"}},
        "value_and_theft_sensitivity": {{"explanation": "secure", "concerns": "tampering"}}
    }},
    "product_name": "{product_name}",
    "analysis_timestamp": "{self.current_timestamp}"
    "packaging_location": "{product_inputs.get('packaging_location')}",
    "units_per_shipment": {product_inputs.get('units_per_shipment')},
    "budget_constraint": {product_inputs.get('budget_constraint')}
}}
"""

    def _process_response(self, response_text: str) -> Dict[str, Any]:
        """Process and clean up the response text"""
        try:
            # Clean up response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response JSON: {str(e)}")
            logger.debug(f"Raw response text: {response_text}")
            raise ValueError(f"Invalid JSON response: {str(e)}")

    def _save_json_to_temp(self, data: Dict[str, Any], product_name: str) -> str:
        """Save analysis data to temp directory with error handling"""
        try:
            filename = f"{product_name.lower().replace(' ', '_')}_compatibility_report.json"
            filepath = os.path.join(self.temp_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved analysis report to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save analysis report: {str(e)}", exc_info=True)
            raise

# Testing function
async def main():
    """Main function for testing the agent"""
    try:
        logger.info("Starting ProductCompatibilityAgent test")
        agent = ProductCompatibilityAgent()

        # Test product details
        product_name = "Test Product"
        product_inputs = {
            "product_name": product_name,
            "units_per_shipment": 100,
            "dimensions": {"length": 20, "width": 15, "height": 10},
            "packaging_location": "Warehouse A",
            "budget_constraint": 1000.0
        }

        # Run analysis
        analysis = await agent.analyze_product_compatibility(product_name, product_inputs)
        
        # Print results
        print("\nAnalysis Results:")
        print(json.dumps(analysis, indent=2))

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())