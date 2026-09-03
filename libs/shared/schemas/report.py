"""
libs/shared/schemas/report.py — schema for OrchestrationAgent executive summary.

Agent method: OrchestrationAgent.generate_executive_summary()
"""

from __future__ import annotations

from typing import List, Dict

from pydantic import BaseModel

from libs.shared.schemas.base import AgentMetadata


class CompositeMetrics(BaseModel):
    """The individual dimension scores that feed into the composite."""

    properties: float
    logistics: float
    cost: float
    sustainability: float
    consumer: float


class CompositeScore(BaseModel):
    """Composite score plus its per-dimension breakdown."""

    composite: float
    metrics: CompositeMetrics


class ExecutiveSummaryReport(BaseModel):
    """
    Typed output of OrchestrationAgent.generate_executive_summary().

    This is the final artefact surfaced to the React frontend and, in later
    phases, serialised as the REST API response body.
    """

    executive_snapshot: str
    composite_score: CompositeScore
    strengths: List[str]
    trade_offs: List[str]
    supply_chain_implications: str
    consulting_recommendation: str
    regulatory_context: str = ""
    fact_provenance: List[Dict[str, str]] = []
    metadata: AgentMetadata
