"""
libs/shared — centralised settings and typed schemas for the
Sustainable Packaging multi-agent platform.

Public API re-exported here so callers can do:
    from libs.shared import settings, schemas
"""

from libs.shared import schemas
from libs.shared.settings import get_settings

settings = get_settings()

__all__ = ["settings", "get_settings", "schemas"]
