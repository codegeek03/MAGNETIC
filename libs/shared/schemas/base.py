"""
libs/shared/schemas/base.py — shared primitives reused across all agent schemas.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, model_validator


class AgentMetadata(BaseModel):
    """Provenance fields attached to every agent output."""

    timestamp: str
    """UTC timestamp string 'YYYY-MM-DD HH:MM:SS' captured at agent init."""

    user: str
    """Display name of the operator who triggered the analysis run."""

    report_path: Optional[str] = None
    """Filesystem path where the agent saved its raw JSON artefact, if any."""


class AnalysisWeights(BaseModel):
    """
    Composite scoring weights — must sum to 1.0.

    Used as a Pydantic model (rather than a plain dict) so that weight
    validation is enforced at runtime whenever weights are passed around.
    """

    properties: float = 0.1
    logistics: float = 0.1
    cost: float = 0.1
    sustainability: float = 0.4
    consumer: float = 0.3  # 0.1+0.1+0.1+0.4+0.3 = 1.0

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "AnalysisWeights":
        total = (
            self.properties
            + self.logistics
            + self.cost
            + self.sustainability
            + self.consumer
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"AnalysisWeights must sum to 1.0, got {total:.4f}"
            )
        return self
