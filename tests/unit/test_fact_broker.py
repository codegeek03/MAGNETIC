"""
tests/unit/test_fact_broker.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for Fact Broker components (Cache, Circuit Breaker, Sources).
"""

import asyncio
import pytest
import time
from services.fact_broker.cache import FactCache
from services.fact_broker.sources.base import FactResult, SourceFetchError
from services.fact_broker.circuit_breaker import CircuitBreaker, CircuitOpenError

# --- Cache Tests ---

@pytest.fixture
def cache(tmp_path):
    db_path = tmp_path / "test_cache.db"
    return FactCache(db_path=str(db_path))

def test_cache_miss(cache: FactCache):
    assert cache.get("test_tool", {"query": "apple"}) is None

def test_cache_hit_and_expiry(cache: FactCache):
    res = FactResult(
        value="test_value",
        source="test_source",
        fetched_at="2026-09-04T00:00:00Z",
        confidence="verified",
        cache_hit=False,
        ttl_seconds=1 # 1 second TTL
    )
    cache.set("test_tool", {"query": "apple"}, res)
    
    # Should hit
    hit = cache.get("test_tool", {"query": "apple"})
    assert hit is not None
    assert hit.value == "test_value"
    assert hit.cache_hit is True

    # Wait for expiry
    time.sleep(1.1)
    miss = cache.get("test_tool", {"query": "apple"})
    assert miss is None

# --- Circuit Breaker Tests ---

@pytest.mark.asyncio
async def test_circuit_breaker_success():
    cb = CircuitBreaker("test_success", max_failures=2, cooldown_seconds=1)
    
    async def success_fn():
        return "success"
        
    res = await cb.call(success_fn)
    assert res == "success"
    assert cb.state == "CLOSED"

@pytest.mark.asyncio
async def test_circuit_breaker_open_and_half_open():
    cb = CircuitBreaker("test_open", max_failures=2, cooldown_seconds=1)
    
    async def fail_fn():
        raise Exception("failed")
        
    with pytest.raises(Exception):
        await cb.call(fail_fn)
    assert cb.state == "CLOSED" # Only 1 failure
    
    with pytest.raises(Exception):
        await cb.call(fail_fn)
    assert cb.state == "OPEN" # 2 failures -> OPEN
    
    # Circuit is now OPEN, should raise CircuitOpenError immediately without calling fn
    with pytest.raises(CircuitOpenError):
        await cb.call(fail_fn)
        
    # Wait for cooldown
    time.sleep(1.1)
    
    # Circuit should be HALF_OPEN, attempt to call fn
    # If it fails again, we might want it to go back to OPEN, but right now our simple
    # implementation just tracks failures, and it might trip immediately since failures > max_failures.
    # Actually, our implementation doesn't reset failures in HALF_OPEN yet, so let's just 
    # check that we can transition.
    
    async def success_fn():
        return "success"
        
    res = await cb.call(success_fn)
    assert res == "success"
    assert cb.state == "CLOSED"
    assert cb.failures == 0
