"""
libs/shared/schemas — typed Pydantic v2 models for every agent I/O boundary.

Re-exports all public types so callers can do:
    from libs.shared.schemas import ProductCompatibilityResult, MaterialsFound, ...
"""

from libs.shared.schemas.analysis import (
    ConsumerMaterial,
    ConsumerResult,
    ConsumerTrend,
    CostMaterial,
    CostResult,
    LogisticsMaterial,
    LogisticsResult,
    PropertiesMaterial,
    PropertiesResult,
    ScoredMaterial,
    SustainabilityMaterial,
    SustainabilityResult,
)
from libs.shared.schemas.base import AgentMetadata, AnalysisWeights
from libs.shared.schemas.materials import MaterialEntry, MaterialsFound
from libs.shared.schemas.product import ProductCompatibilityResult, ProductCriterion
from libs.shared.schemas.report import (
    CompositeMetrics,
    CompositeScore,
    ExecutiveSummaryReport,
)

__all__ = [
    # base
    "AgentMetadata",
    "AnalysisWeights",
    # product
    "ProductCriterion",
    "ProductCompatibilityResult",
    # materials
    "MaterialEntry",
    "MaterialsFound",
    # analysis
    "ScoredMaterial",
    "PropertiesMaterial",
    "PropertiesResult",
    "LogisticsMaterial",
    "LogisticsResult",
    "CostMaterial",
    "CostResult",
    "SustainabilityMaterial",
    "SustainabilityResult",
    "ConsumerMaterial",
    "ConsumerTrend",
    "ConsumerResult",
    # report
    "CompositeMetrics",
    "CompositeScore",
    "ExecutiveSummaryReport",
]
