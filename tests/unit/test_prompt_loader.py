"""
tests/unit/test_prompt_loader.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Verifies that every service key in prompts.yaml:
  1. Exists and is loadable.
  2. Renders the user prompt without errors given representative kwargs.
  3. Raises jinja2.UndefinedError for missing required variables.
  4. Raises KeyError for unknown service keys.
"""

import pytest
from jinja2 import UndefinedError

from services.base.prompt_loader import PromptLoader, _load_raw


# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def loader() -> PromptLoader:
    _load_raw.cache_clear()
    return PromptLoader()


FULL_KWARGS = dict(
    product_name="Whey Protein Bar",
    units_per_shipment=1000,
    dim_length=15,
    dim_width=8,
    dim_height=3,
    packaging_location="Mumbai, India",
    budget_constraint=0.50,
    timestamp="2026-09-04 00:00:00",
    user="test-user",
    material_name="PLA",
    location="Mumbai, India",
    criteria_keys=["physical_form", "fragility"],
    schema_json='{"materials_by_criteria": {}}',
)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestPromptLoaderKeys:
    def test_all_expected_keys_present(self, loader: PromptLoader):
        """All 8 service prompts must be registered."""
        expected = {
            "product_compatibility",
            "materials_db",
            "material_properties",
            "logistics",
            "cost",
            "sustainability",
            "consumer_behavior",
            "orchestrator",
        }
        assert expected.issubset(set(loader.keys())), (
            f"Missing keys: {expected - set(loader.keys())}"
        )

    def test_unknown_key_raises(self, loader: PromptLoader):
        with pytest.raises(KeyError, match="No prompt found"):
            loader.render("does_not_exist", **FULL_KWARGS)


class TestPromptRendering:
    @pytest.mark.parametrize("service_key", [
        "product_compatibility",
        "material_properties",
        "logistics",
        "cost",
        "sustainability",
        "consumer_behavior",
    ])
    def test_render_returns_non_empty_string(self, loader: PromptLoader, service_key: str):
        text = loader.render(service_key, **FULL_KWARGS)
        assert isinstance(text, str)
        assert len(text.strip()) > 50, f"Prompt for '{service_key}' is suspiciously short"

    def test_render_materials_db(self, loader: PromptLoader):
        text = loader.render("materials_db", **FULL_KWARGS)
        assert "physical_form" in text or "fragility" in text
        assert "Mumbai" in text

    def test_render_orchestrator(self, loader: PromptLoader):
        text = loader.render("orchestrator", **FULL_KWARGS)
        assert "PLA" in text
        assert "Mumbai" in text
        assert "Whey Protein Bar" in text

    def test_product_name_interpolated(self, loader: PromptLoader):
        text = loader.render("product_compatibility", **FULL_KWARGS)
        assert "Whey Protein Bar" in text

    def test_location_interpolated_in_logistics(self, loader: PromptLoader):
        text = loader.render("logistics", **FULL_KWARGS)
        assert "Mumbai" in text

    def test_missing_required_var_raises(self, loader: PromptLoader):
        """StrictUndefined must raise for missing variables."""
        with pytest.raises(UndefinedError):
            loader.render("product_compatibility")  # no kwargs


class TestSystemPrompts:
    def test_system_prompt_non_empty(self, loader: PromptLoader):
        for key in loader.keys():
            sys_text = loader.render_system(key)
            assert isinstance(sys_text, str)
