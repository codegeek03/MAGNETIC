"""
libs/shared/schemas/materials.py — schemas for PackagingMaterialsAgent output.

Agent method: PackagingMaterialsAgent.find_materials_by_criteria()
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel

from libs.shared.schemas.base import AgentMetadata


class MaterialEntry(BaseModel):
    """A single candidate packaging material."""

    material_name: str
    type: str


class MaterialsFound(BaseModel):
    """
    Typed output of PackagingMaterialsAgent.find_materials_by_criteria().

    ``materials`` maps category names (e.g. "bio_based", "recycled",
    "conventional") to lists of MaterialEntry objects.
    """

    product_name: str
    materials: Dict[str, List[MaterialEntry]]
    metadata: AgentMetadata
