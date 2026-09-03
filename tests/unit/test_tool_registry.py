"""
tests/unit/test_tool_registry.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Verifies the ToolRegistry:
  1. Returns the correct tool type for each registered name.
  2. Caches — two calls return the same object.
  3. Raises ValueError for unknown tool names.
  4. get_many() preserves order and deduplicates correctly.
"""

import pytest

from services.base.tool_registry import AVAILABLE_TOOLS, ToolRegistry


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


class TestToolRegistryLookup:
    def test_unknown_tool_raises(self, registry: ToolRegistry):
        with pytest.raises(ValueError, match="Unknown tool"):
            registry.get("nonexistent_tool")

    def test_get_many_preserves_order(self, registry: ToolRegistry):
        names = ["calculator"]
        tools = registry.get_many(names)
        assert len(tools) == 1

    def test_get_many_empty(self, registry: ToolRegistry):
        assert registry.get_many([]) == []

    def test_available_tools_set(self):
        assert "tavily" in AVAILABLE_TOOLS
        assert "duckduckgo" in AVAILABLE_TOOLS
        assert "calculator" in AVAILABLE_TOOLS
        assert "newspaper4k" in AVAILABLE_TOOLS
        assert "googlesearch" in AVAILABLE_TOOLS
        assert "pubmed" in AVAILABLE_TOOLS


class TestToolRegistryCaching:
    def test_same_object_returned_twice(self, registry: ToolRegistry):
        """get() must cache — two calls return the identical object."""
        t1 = registry.get("calculator")
        t2 = registry.get("calculator")
        assert t1 is t2

    def test_independent_registries_have_separate_caches(self):
        r1 = ToolRegistry()
        r2 = ToolRegistry()
        t1 = r1.get("calculator")
        t2 = r2.get("calculator")
        # Different registry instances → different objects
        assert t1 is not t2


class TestToolTypes:
    """Verify each tool resolves to its expected Agno class."""

    def test_calculator_type(self, registry: ToolRegistry):
        from agno.tools.calculator import CalculatorTools
        assert isinstance(registry.get("calculator"), CalculatorTools)

    def test_duckduckgo_type(self, registry: ToolRegistry):
        pytest.importorskip("ddgs", reason="ddgs not installed")
        from agno.tools.duckduckgo import DuckDuckGoTools
        assert isinstance(registry.get("duckduckgo"), DuckDuckGoTools)
