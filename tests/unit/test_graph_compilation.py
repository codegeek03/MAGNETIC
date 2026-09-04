"""Tests asserting that the LangGraph workflow compiles correctly."""

from main import create_analysis_graph


def test_create_analysis_graph_compilation():
    """Verify that create_analysis_graph compiles without error into a runnable graph."""
    graph = create_analysis_graph()
    assert graph is not None

    # Check that all expected workflow nodes are registered in the graph
    expected_nodes = {
        "input",
        "compatibility",
        "material_db",
        "properties",
        "logistics",
        "costs",
        "sustainability",
        "consumer",
        "route_phase_2",
        "carbon_lca",
        "compliance_doc",
        "orchestrator",
        "error_handler",
    }

    graph_nodes = set(graph.nodes.keys())
    for node in expected_nodes:
        assert (
            node in graph_nodes
        ), f"Expected node '{node}' not found in compiled graph nodes: {graph_nodes}"


def test_graph_has_checkpointer():
    """Verify that the compiled graph has a checkpointer configured."""
    graph = create_analysis_graph()
    assert hasattr(graph, "checkpointer")
    assert graph.checkpointer is not None
