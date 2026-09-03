"""
services/base — shared abstractions for all service agents.

Import BaseAgent directly from services.base.agent to avoid pulling
in agno at test-collection time for tests that only need PromptLoader
or ToolRegistry.
"""

from services.base.prompt_loader import PromptLoader
from services.base.tool_registry import ToolRegistry

__all__ = ["PromptLoader", "ToolRegistry"]
