"""
services/base/prompt_loader.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Loads ``prompts/prompts.yaml`` once and renders Jinja2 templates on demand.

Usage::

    loader = PromptLoader()                        # reads YAML once
    text = loader.render("sustainability",
                         product_name="Protein Bar",
                         timestamp="2026-09-04 00:00:00",
                         user="alice")
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Resolve path relative to the project root (two levels up from this file)
_PROMPTS_PATH = Path(__file__).resolve().parents[2] / "prompts" / "prompts.yaml"


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    """Parse prompts.yaml exactly once and cache the result."""
    try:
        import yaml  # pyyaml
    except ImportError as exc:
        raise ImportError(
            "pyyaml is required for PromptLoader. "
            "Run: pip install pyyaml"
        ) from exc

    with _PROMPTS_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    logger.debug("PromptLoader: loaded %d service keys from %s", len(data), _PROMPTS_PATH)
    return data


class PromptLoader:
    """
    Renders Jinja2-templated prompts from ``prompts/prompts.yaml``.

    Each top-level YAML key maps to one service (e.g. ``product_compatibility``).
    Under each key, ``system`` and ``user`` sub-keys hold the template strings.
    """

    def __init__(self) -> None:
        try:
            from jinja2 import Environment, StrictUndefined
        except ImportError as exc:
            raise ImportError(
                "jinja2 is required for PromptLoader. "
                "Run: pip install jinja2"
            ) from exc

        self._env = Environment(
            undefined=StrictUndefined,  # raise on missing variables
            keep_trailing_newline=True,
        )
        self._raw = _load_raw()

    # ── public API ────────────────────────────────────────────────────────────

    def render(self, service_key: str, **kwargs: Any) -> str:
        """Render the *user* prompt template for *service_key*.

        Parameters
        ----------
        service_key:
            Must match a top-level key in prompts.yaml.
        **kwargs:
            Template variables (e.g. ``product_name``, ``location``).

        Raises
        ------
        KeyError
            If *service_key* is not found in the YAML.
        jinja2.UndefinedError
            If a required template variable is missing from *kwargs*.
        """
        block = self._raw.get(service_key)
        if block is None:
            available = ", ".join(sorted(self._raw.keys()))
            raise KeyError(
                f"No prompt found for service key '{service_key}'. "
                f"Available keys: {available}"
            )
        user_template = block.get("user", "")
        return self._env.from_string(user_template).render(**kwargs)

    def render_system(self, service_key: str, **kwargs: Any) -> str:
        """Render the *system* prompt template for *service_key*."""
        block = self._raw.get(service_key, {})
        system_template = block.get("system", "")
        return self._env.from_string(system_template).render(**kwargs)

    def keys(self) -> list[str]:
        """Return all registered service keys."""
        return list(self._raw.keys())
