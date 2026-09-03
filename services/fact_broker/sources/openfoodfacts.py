"""
services/fact_broker/sources/openfoodfacts.py
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from services.fact_broker.sources.base import SourceClient, SourceFetchError


class OpenFoodFactsSource(SourceClient):
    name: ClassVar[str] = "openfoodfacts"
    confidence: ClassVar[str] = "verified"

    def __init__(self) -> None:
        self.base_url = "https://world.openfoodfacts.org/cgi/search.pl"

    async def fetch(self, product_category: str, country: str) -> str:
        try:
            params = {
                "action": "process",
                "tagtype_0": "categories",
                "tag_contains_0": "contains",
                "tag_0": product_category,
                "json": "1",
                "page_size": "20",
                "fields": "packaging,packaging_tags"
            }
            if country:
                params.update({
                    "tagtype_1": "countries",
                    "tag_contains_1": "contains",
                    "tag_1": country
                })

            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

                products = data.get("products", [])
                materials = set()
                for p in products:
                    tags = p.get("packaging_tags", [])
                    for t in tags:
                        materials.add(t)

                if materials:
                    return f"Common packaging materials for {product_category} in {country}: {', '.join(materials)}"
                else:
                    return f"No packaging data found for {product_category} in {country} on Open Food Facts."
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"Open Food Facts fetch failed: {exc}")
