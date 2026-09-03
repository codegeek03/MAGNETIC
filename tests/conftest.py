"""Pytest fixtures and configuration for offline smoke testing."""

import os
from typing import Any, Dict

import pytest

# Ensure test environment variables exist before any module load
os.environ.setdefault("GOOGLE_API_KEY", "test-mock-google-api-key")
os.environ.setdefault("TAVILY_API_KEY", "test-mock-tavily-api-key")


@pytest.fixture
def mock_env_keys(monkeypatch):
    """Ensure environment variables are populated with test keys."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-mock-google-api-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-mock-tavily-api-key")


@pytest.fixture
def sample_input_data() -> Dict[str, Any]:
    """Sample product input data for testing the graph pipeline."""
    return {
        "product_name": "Organic Coffee Beans",
        "category": "Food & Beverage",
        "packaging_location": "California, USA",
        "physical_state": "Solid",
        "dimensions": {"length": 10.0, "width": 5.0, "height": 15.0},
        "weight": 500.0,
        "fragility": "Low",
        "perishability": "Medium",
        "moisture_sensitivity": "High",
        "light_sensitivity": "High",
        "shelf_life_days": 180,
        "storage_conditions": "Cool and dry",
        "target_market": "North America",
        "cost_sensitivity": "Medium",
        "target_cost": 0.50,
        "sustainability_goals": "Zero plastic, 100% compostable",
        "properties_weight": 0.1,
        "logistics_weight": 0.1,
        "cost_weight": 0.1,
        "sustainability_weight": 0.4,
        "consumer_weight": 0.2,
    }


@pytest.fixture
def sample_compatibility_result() -> Dict[str, Any]:
    """Mock result from ProductCompatibilityAgent."""
    return {
        "compatible_material_types": ["Bio-based polymer", "Kraft paper"],
        "barrier_requirements": ["High moisture barrier", "Oxygen barrier"],
        "compatibility_score": 8.5,
    }


@pytest.fixture
def sample_material_db_result() -> Dict[str, Any]:
    """Mock result from PackagingMaterialsAgent."""
    return {
        "materials": {
            "bio_based": [
                {
                    "material_id": "mat-001",
                    "material_name": "PLA-Lined Kraft Paper",
                    "type": "Composite Paper",
                    "description": "Kraft paper laminated with poly-lactic acid.",
                }
            ]
        }
    }


@pytest.fixture
def sample_properties_result() -> Dict[str, Any]:
    """Mock result from MaterialPropertiesAgent."""
    return {
        "top_materials": [
            {
                "material_name": "PLA-Lined Kraft Paper",
                "overall_score": 8.0,
                "tensile_strength": 45.0,
                "barrier_properties": {"moisture": "Good", "oxygen": "Moderate"},
            }
        ]
    }


@pytest.fixture
def sample_logistics_result() -> Dict[str, Any]:
    """Mock result from LogisticCompatibilityAgent."""
    return {
        "top_materials": [
            {
                "material_name": "PLA-Lined Kraft Paper",
                "logistics_score": 8.0,
                "shipping_efficiency": "High",
            }
        ]
    }


@pytest.fixture
def sample_cost_result() -> Dict[str, Any]:
    """Mock result from ProductionCostAgent."""
    return {
        "top_materials": [
            {
                "material_name": "PLA-Lined Kraft Paper",
                "cost_score": 7.5,
                "unit_cost_estimate": 0.35,
            }
        ]
    }


@pytest.fixture
def sample_sustainability_result() -> Dict[str, Any]:
    """Mock result from EnvironmentalImpactAgent."""
    return {
        "top_materials": [
            {
                "material_name": "PLA-Lined Kraft Paper",
                "environmental_score": 9.0,
                "carbon_footprint_kg": 0.12,
                "recyclability": "Compostable",
            }
        ]
    }


@pytest.fixture
def sample_consumer_result() -> Dict[str, Any]:
    """Mock result from ConsumerBehaviorAgent."""
    return {
        "top_materials": [
            {
                "material_name": "PLA-Lined Kraft Paper",
                "overall_consumer_score": 8.5,
                "consumer_sentiment": "Positive",
            }
        ]
    }


@pytest.fixture
def sample_executive_summary() -> Dict[str, Any]:
    """Mock executive summary for one material from OrchestrationAgent."""
    return {
        "executive_snapshot": "Recommended for high sustainability and solid performance.",
        "composite_score": {
            "composite": 8.2,
            "metrics": {
                "properties": 8.0,
                "logistics": 8.0,
                "cost": 7.5,
                "sustainability": 9.0,
                "consumer": 8.5,
            },
        },
        "strengths": ["Excellent compostability", "Good barrier protection"],
        "trade_offs": ["Slightly higher cost than conventional plastic"],
        "supply_chain_implications": {"availability": "Widely available in NA"},
        "consulting_recommendation": {"action": "Proceed with pilot production run"},
    }

@pytest.fixture(autouse=True)
def mock_tool_registry(monkeypatch):
    """
    Mock the Fact Broker MCP tool so the test suite can run offline
    without requiring the FastMCP server to be running.
    """
    from services.base.tool_registry import ToolRegistry

    original_build = ToolRegistry._build

    def mock_build(self, name: str):
        if name == "fact_broker":
            from agno.tools import Tool
            class MockFactBroker(Tool):
                def __init__(self):
                    super().__init__(name="fact_broker", description="Mock Fact Broker")
                def run(self, *args, **kwargs):
                    return "Mocked Fact Broker result"
            return MockFactBroker()
        return original_build(self, name)

    monkeypatch.setattr(ToolRegistry, "_build", mock_build)
