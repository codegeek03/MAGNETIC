"""Tests asserting graph routing logic and end-to-end execution with mocked agents."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from main import (
    check_phase_1_completion,
    create_analysis_graph,
    route_phase_1,
)


def test_route_phase_1_success(sample_material_db_result):
    """Routing should proceed to agent nodes when materials are found and no error."""
    state = {
        "material_database": sample_material_db_result,
        "error": "",
    }
    with patch("main.registry.get_agents_for_phase", return_value=["dummy_agent"]):
        decision = route_phase_1(state)
        # decision is a list of Send objects
        assert len(decision) == 1
        assert decision[0].node == "dummy_agent"


def test_route_phase_1_empty():
    """Routing should proceed to error_handler when materials dict or list is empty."""
    state = {
        "material_database": {"materials": {}},
        "error": "",
    }
    decision = route_phase_1(state)
    assert decision == ["error_handler"]


def test_route_phase_1_with_error():
    """Routing should proceed to error_handler when state has an error."""
    state = {
        "material_database": {"materials": {"bio": [{"material_name": "Test"}]}},
        "error": "Database lookup timed out",
    }
    decision = route_phase_1(state)
    assert decision == ["error_handler"]


def test_check_phase_1_completion_success():
    """Routing should proceed to route_phase_2 when no error exists."""
    state = {
        "error": "",
    }
    decision = check_phase_1_completion(state)
    assert decision == "route_phase_2"


def test_check_phase_1_completion_with_error():
    """Routing should proceed to error_handler if error is set."""
    state = {
        "error": "Transient failure occurred",
    }
    decision = check_phase_1_completion(state)
    assert decision == "error_handler"


@pytest.mark.asyncio
async def test_graph_execution_happy_path(
    sample_input_data,
    sample_compatibility_result,
    sample_material_db_result,
    sample_properties_result,
    sample_logistics_result,
    sample_cost_result,
    sample_sustainability_result,
    sample_consumer_result,
    sample_executive_summary,
):
    """End-to-end execution of compiled graph with all agent calls mocked."""
    graph = create_analysis_graph()

    with patch("main.ProductCompatibilityAgent") as mock_compat_cls, \
         patch("main.PackagingMaterialsAgent") as mock_mat_cls, \
         patch("main.MaterialPropertiesAgent") as mock_props_cls, \
         patch("main.LogisticCompatibilityAgent") as mock_log_cls, \
         patch("main.ProductionCostAgent") as mock_cost_cls, \
         patch("main.EnvironmentalImpactAgent") as mock_sust_cls, \
         patch("main.ConsumerBehaviorAgent") as mock_cons_cls, \
         patch("main.OrchestrationAgent") as mock_orch_cls:

        mock_compat_cls.return_value.analyze_product_compatibility = AsyncMock(
            return_value=sample_compatibility_result
        )
        mock_mat_cls.return_value.find_materials_by_criteria = AsyncMock(
            return_value=sample_material_db_result
        )
        mock_props_cls.return_value.analyze_material_properties = AsyncMock(
            return_value=sample_properties_result
        )
        mock_log_cls.return_value.analyze_top_logistics_materials = AsyncMock(
            return_value=sample_logistics_result
        )
        mock_cost_cls.return_value.analyze_production_costs = AsyncMock(
            return_value=sample_cost_result
        )
        mock_sust_cls.return_value.analyze_environmental_impact = AsyncMock(
            return_value=sample_sustainability_result
        )
        mock_cons_cls.return_value.analyze_consumer_behavior = AsyncMock(
            return_value=sample_consumer_result
        )
        mock_orch_instance = mock_orch_cls.return_value
        mock_orch_instance.generate_executive_summary = AsyncMock(
            return_value=sample_executive_summary
        )
        mock_orch_instance._save_report = MagicMock(return_value="temp_KB/reports/mock_report.json")

        initial_state = {
            "input_data": sample_input_data,
            "error": "",
        }
        config = {"configurable": {"thread_id": "test-session-001"}}

        final_state = await graph.ainvoke(initial_state, config=config)

        assert final_state["compatibility_status"] == "completed"
        assert final_state["material_db_status"] == "completed"
        assert final_state["properties_status"] == "completed"
        assert final_state["logistics_status"] == "completed"
        assert final_state["costs_status"] == "completed"
        assert final_state["sustainability_status"] == "completed"
        assert final_state["consumer_status"] == "completed"
        assert final_state["orchestration_status"] == "completed"
        assert "final_results" in final_state
        assert "material_summaries" in final_state["final_results"]
        assert len(final_state["final_results"]["material_summaries"]) > 0


@pytest.mark.asyncio
async def test_graph_execution_material_db_failure_routes_to_error_handler(
    sample_input_data,
    sample_compatibility_result,
):
    """When material DB returns no materials, the graph should route to error_handler."""
    graph = create_analysis_graph()

    with patch("main.ProductCompatibilityAgent") as mock_compat_cls, \
         patch("main.PackagingMaterialsAgent") as mock_mat_cls, \
         patch("main.OrchestrationAgent") as mock_orch_cls:

        mock_compat_cls.return_value.analyze_product_compatibility = AsyncMock(
            return_value=sample_compatibility_result
        )
        # Return empty materials to simulate lookup failure
        mock_mat_cls.return_value.find_materials_by_criteria = AsyncMock(
            return_value={"materials": {}}
        )
        mock_orch_instance = mock_orch_cls.return_value
        mock_orch_instance.analyze_error = AsyncMock(
            return_value={"root_cause_analysis": {"likely_cause": "No materials available"}}
        )
        mock_orch_instance._save_report = MagicMock(
            return_value="temp_KB/reports/mock_error_report.json"
        )

        initial_state = {
            "input_data": sample_input_data,
            "error": "",
        }
        config = {"configurable": {"thread_id": "test-session-err-001"}}

        final_state = await graph.ainvoke(initial_state, config=config)

        assert final_state["material_db_status"] == "failed"
        assert "error" in final_state
        assert "final_results" in final_state
        assert "error" in final_state["final_results"]
