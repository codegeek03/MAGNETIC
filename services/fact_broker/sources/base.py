"""
services/fact_broker/sources/base.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Abstract base for Fact Broker sources.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Optional


@dataclass
class FactResult:
    """Standardised response from the Fact Broker."""
    value: str
    source: str
    fetched_at: str
    confidence: str
    cache_hit: bool
    ttl_seconds: int

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "source": self.source,
            "fetched_at": self.fetched_at,
            "confidence": self.confidence,
            "cache_hit": self.cache_hit,
            "ttl_seconds": self.ttl_seconds,
        }


class SourceFetchError(Exception):
    """Raised when a source fails to fetch."""
    pass


class SourceClient(ABC):
    """
    Base class for a Fact Broker source.
    """
    name: ClassVar[str]
    confidence: ClassVar[str]

    @abstractmethod
    async def fetch(self, **kwargs) -> str:
        """Fetch raw text from the source. Subclasses must implement."""
        pass
