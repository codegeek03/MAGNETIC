"""
services/fact_broker/sources/alphavantage.py
"""

from __future__ import annotations

import httpx
from typing import ClassVar
from services.fact_broker.sources.base import SourceClient, SourceFetchError


class AlphaVantageSource(SourceClient):
    name: ClassVar[str] = "alphavantage"
    confidence: ClassVar[str] = "estimated"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"

    async def fetch(self, commodity: str) -> str:
        if not self.api_key:
            raise SourceFetchError("ALPHAVANTAGE_API_KEY is not set")
            
        try:
            params = {
                "function": commodity, # e.g. ALUMINUM, COPPER
                "interval": "monthly",
                "apikey": self.api_key
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if "Information" in data: # Usually an error message or rate limit
                    raise SourceFetchError(data["Information"])
                
                if "data" in data and len(data["data"]) > 0:
                    latest = data["data"][0]
                    return f"{commodity} proxy index value: {latest['value']} as of {latest['date']}"
                
                return f"No recent data for {commodity}"
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"Alpha Vantage fetch failed: {exc}")
