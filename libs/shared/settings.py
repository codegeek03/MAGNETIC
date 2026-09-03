"""
Centralised settings for the Sustainable Packaging multi-agent platform.

All agents import from here instead of hardcoding constants.
Env vars are loaded from a .env file (if present) via pydantic-settings.

Usage:
    from libs.shared.settings import get_settings
    settings = get_settings()
    model_id = settings.gemini_model_id
    ts = settings.now_utc()
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict

from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnalysisWeights(BaseModel):
    """
    Weights for the composite scoring formula — must sum to 1.0.

    This is a plain BaseModel (not BaseSettings) so that pydantic-settings'
    field-merging logic never fires the sum validator prematurely.
    Env-var overrides are applied by Settings via ``AnalysisWeights.from_env()``.
    """

    properties: float = 0.1
    logistics: float = 0.1
    cost: float = 0.1
    sustainability: float = 0.4
    consumer: float = 0.3  # 0.1+0.1+0.1+0.4+0.3 = 1.0

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "AnalysisWeights":
        total = (
            self.properties
            + self.logistics
            + self.cost
            + self.sustainability
            + self.consumer
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"AnalysisWeights must sum to 1.0, got {total:.4f}. "
                "Check WEIGHT_* environment variables."
            )
        return self

    @classmethod
    def from_env(cls) -> "AnalysisWeights":
        """Read WEIGHT_* env vars (or .env file) and construct the model."""
        import os

        return cls(
            properties=float(os.getenv("WEIGHT_PROPERTIES", "0.1")),
            logistics=float(os.getenv("WEIGHT_LOGISTICS", "0.1")),
            cost=float(os.getenv("WEIGHT_COST", "0.1")),
            sustainability=float(os.getenv("WEIGHT_SUSTAINABILITY", "0.4")),
            consumer=float(os.getenv("WEIGHT_CONSUMER", "0.3")),
        )

    def as_dict(self) -> Dict[str, float]:
        return {
            "properties": self.properties,
            "logistics": self.logistics,
            "cost": self.cost,
            "sustainability": self.sustainability,
            "consumer": self.consumer,
        }


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables / .env file.

    Priority (highest → lowest):
        1. Actual environment variables
        2. .env file in the project root
        3. Defaults defined below
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    gemini_model_id: str = "gemini-2.0-flash"
    """Gemini model identifier.  Override with GEMINI_MODEL_ID=gemini-2.0-flash-exp."""

    google_api_key: str = ""
    """Google Gemini API key. Must be set via GOOGLE_API_KEY=<your-key>."""

    tavily_api_key: str = ""
    """Optional Tavily search key.  Override with TAVILY_API_KEY=<your-key>."""

    alphavantage_api_key: str = ""
    """Alpha Vantage API key for commodities. Override with ALPHAVANTAGE_API_KEY."""

    brave_api_key: str = ""
    """Brave Search API key. Override with BRAVE_API_KEY."""

    fact_broker_url: str = "http://localhost:8800/sse"
    """Fact Broker MCP Server SSE URL."""

    # ── Identity ──────────────────────────────────────────────────────────────
    current_user: str = "anonymous"
    """Display name embedded in agent reports.  Override with APP_USER=<name>."""

    # ── Storage ───────────────────────────────────────────────────────────────
    reports_dir: str = "temp_KB"
    """Local directory for agent JSON artefacts.  Override with REPORTS_DIR=<path>."""

    # ── Budget ────────────────────────────────────────────────────────────────
    budget_currency: str = "USD"
    """ISO 4217 currency code used when formatting cost outputs."""

    # ── Scoring weights (nested) ──────────────────────────────────────────────
    # Populated lazily; use the property instead of this field directly.
    _weights: AnalysisWeights | None = None

    @property
    def analysis_weights(self) -> AnalysisWeights:
        """Lazily instantiate AnalysisWeights (reads WEIGHT_* env vars)."""
        if self._weights is None:
            object.__setattr__(self, "_weights", AnalysisWeights.from_env())
        return self._weights  # type: ignore[return-value]

    @field_validator("google_api_key")
    @classmethod
    def _warn_if_missing_api_key(cls, v: str) -> str:
        # We warn rather than raise so that unit tests that mock agents can run
        # without a real key.  Agents themselves will fail loudly at init time
        # if the key is absent.
        if not v:
            import warnings

            warnings.warn(
                "GOOGLE_API_KEY is not set. "
                "Agent calls to Gemini will fail at runtime.",
                stacklevel=2,
            )
        return v

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def now_utc() -> str:
        """Return the current UTC time as 'YYYY-MM-DD HH:MM:SS'.

        All agents should call this once during __init__ so their per-run
        timestamp is consistent and live (not frozen).
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application-wide Settings singleton.

    Using lru_cache means the .env file is parsed exactly once per process,
    but tests can override by calling ``get_settings.cache_clear()`` before
    constructing a fresh instance with monkeypatched env vars.
    """
    return Settings()
