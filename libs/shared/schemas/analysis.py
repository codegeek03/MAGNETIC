"""
libs/shared/schemas/analysis.py — schemas for all five parallel analysis agents.

Agents covered:
  - MaterialPropertiesAgent    → PropertiesResult
  - LogisticCompatibilityAgent → LogisticsResult
  - ProductionCostAgent        → CostResult
  - EnvironmentalImpactAgent   → SustainabilityResult
  - ConsumerBehaviorAgent      → ConsumerResult
"""

from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, Field

from libs.shared.schemas.base import AgentMetadata

# ── Shared base ──────────────────────────────────────────────────────────────

class ScoredMaterial(BaseModel):
    """Base class for all per-material summary results."""

    material_name: str
    overall_score: float
    """Composite score 0–10 (field name varies per agent; see subclasses)."""
    confidence: Literal["verified", "estimated"]
    source: str = ""
    """Provenance citation for the score (e.g., 'EUR-Lex PPWR Art. 6', 'DEFRA 2025')."""


# ── Material Properties ───────────────────────────────────────────────────────

class PropertiesDetail(BaseModel):
    property_scores: Dict[str, float]
    """Dict of individual property scores, e.g. {"tensile_strength": 8.2, ...}"""

class PropertiesSummary(ScoredMaterial):
    key_tradeoff: str

class PropertiesMaterial(BaseModel):
    """Per-material output from MaterialPropertiesAgent."""
    detail: PropertiesDetail
    summary: PropertiesSummary


class PropertiesResult(BaseModel):
    """Typed output of MaterialPropertiesAgent.analyze_material_properties()."""
    top_materials: List[PropertiesMaterial]
    metadata: AgentMetadata


# ── Logistics ─────────────────────────────────────────────────────────────────

class LogisticsDetail(BaseModel):
    primary_advantage: str
    cost_consideration: str

class LogisticsSummary(ScoredMaterial):
    key_tradeoff: str

class LogisticsMaterial(BaseModel):
    """Per-material output from LogisticCompatibilityAgent."""
    detail: LogisticsDetail
    summary: LogisticsSummary


class LogisticsResult(BaseModel):
    """Typed output of LogisticCompatibilityAgent.analyze_top_logistics_materials()."""
    top_materials: List[LogisticsMaterial]
    metadata: AgentMetadata


# ── Production Cost ───────────────────────────────────────────────────────────

class CostDetail(BaseModel):
    base_price: str
    total_estimated_cost: str
    key_costs: List[str]

class CostSummary(ScoredMaterial):
    key_tradeoff: str

class CostMaterial(BaseModel):
    """Per-material output from ProductionCostAgent."""
    detail: CostDetail
    summary: CostSummary


class CostResult(BaseModel):
    """Typed output of ProductionCostAgent.analyze_production_costs()."""
    top_materials: List[CostMaterial]
    metadata: AgentMetadata


# ── Environmental / Sustainability ───────────────────────────────────────────

class SustainabilityDetail(BaseModel):
    key_benefit: str
    primary_concern: str

class SustainabilitySummary(ScoredMaterial):
    key_tradeoff: str
    recyclability_grade: str

class SustainabilityMaterial(BaseModel):
    """Per-material output from EnvironmentalImpactAgent."""
    detail: SustainabilityDetail
    summary: SustainabilitySummary


class SustainabilityResult(BaseModel):
    """Typed output of EnvironmentalImpactAgent.analyze_environmental_impact()."""
    top_materials: List[SustainabilityMaterial]
    metadata: AgentMetadata


# ── Consumer Behaviour ────────────────────────────────────────────────────────

class ConsumerMetric(BaseModel):
    """One consumer behaviour dimension for a single material."""
    score: float
    trend_strength: Literal["strong", "moderate", "weak"]
    key_insight: str


class ConsumerDetail(BaseModel):
    consumer_metrics: Dict[str, ConsumerMetric]
    target_demographics: List[str]
    market_positioning: str

class ConsumerSummary(ScoredMaterial):
    key_tradeoff: str

class ConsumerMaterial(BaseModel):
    """Per-material output from ConsumerBehaviorAgent."""
    detail: ConsumerDetail
    summary: ConsumerSummary


class ConsumerTrend(BaseModel):
    """A market trend identified by the ConsumerBehaviorAgent."""
    trend_name: str
    impact_level: Literal["high", "medium", "low"]
    relevance: str


class ConsumerResult(BaseModel):
    """Typed output of ConsumerBehaviorAgent.analyze_consumer_behavior()."""
    top_materials: List[ConsumerMaterial]
    consumer_trends: List[ConsumerTrend]
    metadata: AgentMetadata

# ── Wave 1: Carbon LCA schemas ────────────────────────────────────────────────
class CarbonLcaDetail(BaseModel):
    carbon_delta_kg: float = Field(description="Difference in kg CO2e between current and proposed packaging")
    emission_factors_used: List[str] = Field(description="Source of emission factors (e.g. DEFRA)")
    calculation_breakdown: Dict[str, float] = Field(description="Breakdown of carbon calculation by lifecycle phase")

class CarbonLcaSummary(ScoredMaterial):
    carbon_delta_kg: float = Field(description="Difference in kg CO2e between current and proposed packaging")
    key_carbon_insight: str = Field(description="One line summary of carbon impact")

class CarbonLcaMaterial(BaseModel):
    detail: CarbonLcaDetail
    summary: CarbonLcaSummary

class CarbonLcaResult(BaseModel):
    top_materials: List[CarbonLcaMaterial] = Field(
        description="List of materials with carbon lifecycle analysis"
    )
    metadata: AgentMetadata

# ── Wave 1: Compliance Doc schemas ──────────────────────────────────────────
class ComplianceDocDetail(BaseModel):
    compiled_evidence: List[str] = Field(description="Raw citations and clauses assembled")
    missing_information: List[str] = Field(description="Gaps in the PPWR documentation")

class ComplianceDocSummary(ScoredMaterial):
    doc_status: str = Field(description="Status of the conformity declaration: Drafted, Incomplete, or Failed")
    primary_regulation: str = Field(description="Main regulation governing the pack")

class ComplianceDocMaterial(BaseModel):
    detail: ComplianceDocDetail
    summary: ComplianceDocSummary

class ComplianceDocResult(BaseModel):
    top_materials: List[ComplianceDocMaterial] = Field(
        description="List of materials with their drafted compliance docs"
    )
    metadata: AgentMetadata
