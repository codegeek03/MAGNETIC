"""
services/base/model_router.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Model cascading router that selects the appropriate Gemini model
based on task complexity and provides automatic fallback on failure.

Complexity tiers:
  - "light"  → gemini-2.0-flash  (cheap, fast, good for structured extraction)
  - "heavy"  → gemini-2.5-pro    (expensive, accurate, for synthesis/reasoning)

Fallback: if the light model fails validation, the router retries
once with the heavy model before raising.
"""

from __future__ import annotations

import logging
from typing import Literal

from agno.models.google import Gemini

logger = logging.getLogger(__name__)

TaskComplexity = Literal["light", "heavy"]

# Model mapping — centralised so upgrades are a one-line change
_MODEL_MAP: dict[TaskComplexity, str] = {
    "light": "gemini-2.0-flash",
    "heavy": "gemini-2.5-flash",
}


class ModelRouter:
    """
    Picks the right Gemini model variant based on declared task complexity.

    Usage in a service agent::

        class MyService(BaseAgent):
            task_complexity: ClassVar[TaskComplexity] = "heavy"
    """

    @staticmethod
    def get_model(
        complexity: TaskComplexity = "light",
        *,
        search: bool = True,
        grounding: bool = False,
        temperature: float | None = None,
    ) -> Gemini:
        """Return a configured Gemini model for the given complexity tier."""
        model_id = _MODEL_MAP[complexity]
        kwargs: dict = {
            "id": model_id,
            "search": search,
            "grounding": grounding,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        logger.debug("ModelRouter → %s (complexity=%s)", model_id, complexity)
        return Gemini(**kwargs)

    @staticmethod
    def get_fallback_model(
        complexity: TaskComplexity = "light",
        *,
        search: bool = True,
        grounding: bool = False,
    ) -> Gemini | None:
        """Return a heavier model to fall back to, or None if already at max."""
        if complexity == "heavy":
            return None  # already at the top tier
        return ModelRouter.get_model(
            "heavy", search=search, grounding=grounding
        )
"""
services/base/model_router.py — end
"""
