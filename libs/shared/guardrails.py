"""
libs/shared/guardrails.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Lightweight input/output guardrail system for the packaging analysis platform.

Uses pattern matching for known prompt injection signatures and validates
that safety-critical output claims are grounded in Fact Broker data.

No heavy external dependency (NeMo, Llama Guard) — we keep it simple
and effective using regex + heuristic checks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Known prompt injection patterns ──────────────────────────────────────────

_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"pretend\s+you\s+are", re.I),
    re.compile(r"act\s+as\s+if\s+you", re.I),
    re.compile(r"output\s+(the\s+)?(secret|password|key|token)", re.I),
    re.compile(r"reveal\s+(your|the)\s+(system|initial)\s+prompt", re.I),
]

# ── Safety-critical keywords that require grounding ──────────────────────────

_SAFETY_CLAIMS = [
    "food-safe",
    "food safe",
    "food grade",
    "food-grade",
    "fda approved",
    "fda-approved",
    "non-toxic",
    "nontoxic",
    "bpa-free",
    "bpa free",
    "compostable",
    "biodegradable",
    "recyclable",
]


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""

    passed: bool = True
    blocked: bool = False
    warnings: List[str] = field(default_factory=list)
    reason: str = ""


class InputGuard:
    """
    Validates user inputs against known prompt injection patterns.

    Returns a GuardrailResult with blocked=True if injection is detected.
    """

    @staticmethod
    def check(text: str) -> GuardrailResult:
        """Screen input text for prompt injection attempts."""
        for pattern in _INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                logger.warning(
                    "InputGuard: blocked prompt injection attempt: '%s'",
                    match.group()[:80],
                )
                return GuardrailResult(
                    passed=False,
                    blocked=True,
                    reason=f"Input blocked: suspected prompt injection detected.",
                )
        return GuardrailResult(passed=True)


class OutputGuard:
    """
    Validates LLM outputs for ungrounded safety claims.

    If the output contains safety-critical keywords (e.g., "food-safe",
    "FDA approved") without a corresponding entry in fact_provenance,
    a warning is appended to the result.
    """

    @staticmethod
    def check(output: Dict[str, Any]) -> GuardrailResult:
        """Screen output dict for ungrounded safety claims."""
        warnings: List[str] = []

        # Serialise the output to search for keywords
        output_text = str(output).lower()

        # Check for safety claims
        provenance = output.get("fact_provenance", [])
        provenance_text = str(provenance).lower() if provenance else ""

        for claim in _SAFETY_CLAIMS:
            if claim in output_text and claim not in provenance_text:
                warnings.append(
                    f"Ungrounded safety claim detected: '{claim}'. "
                    "This claim lacks fact_provenance citation."
                )

        if warnings:
            logger.warning(
                "OutputGuard: %d ungrounded safety claim(s) detected",
                len(warnings),
            )

        return GuardrailResult(
            passed=len(warnings) == 0,
            warnings=warnings,
        )
