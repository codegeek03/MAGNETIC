"""
services/fact_broker/sources/brave.py
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from services.fact_broker.sources.base import SourceClient, SourceFetchError


class BraveSearchSource(SourceClient):
    name: ClassVar[str] = "brave"
    confidence: ClassVar[str] = "verified"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def fetch(self, query: str) -> str:
        if not self.api_key:
            raise SourceFetchError("BRAVE_API_KEY is not set")

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        params = {"q": query, "count": 3}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                results = data.get("web", {}).get("results", [])
                if not results:
                    return f"No results found for: {query}"

                snippets = []
                for res in results:
                    snippets.append(f"- {res.get('title')}: {res.get('description')} ({res.get('url')})")

                return "\n".join(snippets)
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"Brave Search fetch failed: {exc}")
