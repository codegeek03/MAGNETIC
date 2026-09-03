"""services/fact_broker/sources package."""

from services.fact_broker.sources.base import SourceClient, FactResult, SourceFetchError
from services.fact_broker.sources.eurlex import EurlexSource
from services.fact_broker.sources.openfoodfacts import OpenFoodFactsSource
from services.fact_broker.sources.alphavantage import AlphaVantageSource
from services.fact_broker.sources.brave import BraveSearchSource

__all__ = [
    "SourceClient",
    "FactResult",
    "SourceFetchError",
    "EurlexSource",
    "OpenFoodFactsSource",
    "AlphaVantageSource",
    "BraveSearchSource",
]
