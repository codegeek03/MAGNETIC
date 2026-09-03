"""
libs/shared/schemas/product.py — schemas for ProductCompatibilityAgent output.

Agent method: ProductCompatibilityAgent.analyze_product_compatibility()
"""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel

from libs.shared.schemas.base import AgentMetadata


class ProductCriterion(BaseModel):
    """A single compatibility criterion with its explanation and concerns."""

    explanation: str
    concerns: str


class ProductCompatibilityResult(BaseModel):
    """
    Typed output of ProductCompatibilityAgent.analyze_product_compatibility().

    The ``criteria`` dict maps criterion names (e.g. "physical_form",
    "fragility", "shelf_life", "chemical_properties") to their
    ProductCriterion details.
    The ``scores`` dict maps the same criterion names to float scores 0–10.
    """

    product_name: str
    criteria: Dict[str, ProductCriterion]
    scores: Dict[str, float]
    metadata: AgentMetadata
