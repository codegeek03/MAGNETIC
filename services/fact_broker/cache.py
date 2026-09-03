"""
services/fact_broker/cache.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SQLite-backed read-through cache for Fact Broker.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Optional

from services.fact_broker.sources.base import FactResult

logger = logging.getLogger(__name__)


class FactCache:
    """SQLite-backed cache for FactResult objects with TTL support."""

    def __init__(self, db_path: str = ".fact_cache.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    source TEXT,
                    fetched_at TEXT,
                    confidence TEXT,
                    ttl_seconds INTEGER,
                    expires_at REAL
                )
                """
            )

    def _make_key(self, tool_name: str, kwargs: Dict[str, Any]) -> str:
        # Sort kwargs to ensure deterministic key
        sorted_items = sorted(kwargs.items())
        key_str = f"{tool_name}:{json.dumps(sorted_items)}"
        return sha256(key_str.encode("utf-8")).hexdigest()

    def get(self, tool_name: str, kwargs: Dict[str, Any]) -> Optional[FactResult]:
        key = self._make_key(tool_name, kwargs)
        now = time.time()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM facts WHERE key = ?", (key,))
                row = cursor.fetchone()

                if not row:
                    return None

                if row["expires_at"] < now:
                    cursor.execute("DELETE FROM facts WHERE key = ?", (key,))
                    conn.commit()
                    return None

                return FactResult(
                    value=row["value"],
                    source=row["source"],
                    fetched_at=row["fetched_at"],
                    confidence=row["confidence"],
                    cache_hit=True,
                    ttl_seconds=row["ttl_seconds"],
                )
        except Exception as exc:
            logger.error("FactCache get error: %s", exc)
            return None

    def set(self, tool_name: str, kwargs: Dict[str, Any], result: FactResult) -> None:
        key = self._make_key(tool_name, kwargs)
        expires_at = time.time() + result.ttl_seconds

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO facts
                    (key, value, source, fetched_at, confidence, ttl_seconds, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        result.value,
                        result.source,
                        result.fetched_at,
                        result.confidence,
                        result.ttl_seconds,
                        expires_at,
                    ),
                )
        except Exception as exc:
            logger.error("FactCache set error: %s", exc)

    def invalidate(self, tool_name: str, kwargs: Dict[str, Any]) -> None:
        key = self._make_key(tool_name, kwargs)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM facts WHERE key = ?", (key,))
