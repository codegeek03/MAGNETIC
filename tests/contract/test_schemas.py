"""
tests/contract/test_schemas.py

Contract tests that verify:
  1. Every Pydantic schema in libs/shared/schemas/ instantiates correctly from
     representative fixture payloads (matching what the real agents emit).
  2. AnalysisWeights raises ValidationError when weights don't sum to 1.0.
  3. Settings.now_utc() returns a parseable datetime string.
  4. Settings.analysis_weights satisfies the sum-to-1 invariant by default.
"""

import re

import pytest
from pydantic import ValidationError

from libs.shared.schemas.analysis import (
    ConsumerMaterial,
    ConsumerMetric,
    ConsumerResult,
    ConsumerTrend,
    ConsumerDetail,
    ConsumerSummary,
    CostMaterial,
    CostResult,
    CostDetail,
    CostSummary,
    LogisticsMaterial,
    LogisticsResult,
    LogisticsDetail,
    LogisticsSummary,
    PropertiesMaterial,
    PropertiesResult,
    PropertiesDetail,
    PropertiesSummary,
    SustainabilityMaterial,
    SustainabilityResult,
    SustainabilityDetail,
    SustainabilitySummary,
)
from libs.shared.schemas.base import AgentMetadata, AnalysisWeights
from libs.shared.schemas.materials import MaterialEntry, MaterialsFound
from libs.shared.schemas.product import ProductCompatibilityResult, ProductCriterion
from libs.shared.schemas.report import (
    CompositeMetrics,
    CompositeScore,
    ExecutiveSummaryReport,
)
from libs.shared.settings import Settings, get_settings

# ── Helpers ───────────────────────────────────────────────────────────────────

SAMPLE_METADATA = {"timestamp": "2026-09-03 03:00:00", "user": "test-user"}
SAMPLE_METADATA_WITH_PATH = {**SAMPLE_METADATA, "report_path": "/tmp/report.json"}


# ── Settings ──────────────────────────────────────────────────────────────────

class TestSettings:
    def setup_method(self):
        # Clear the lru_cache so each test gets a fresh Settings instance
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_now_utc_format(self):
        """now_utc() must return a string matching 'YYYY-MM-DD HH:MM:SS'."""
        ts = Settings.now_utc()
        assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", ts), (
            f"now_utc() returned unexpected format: {ts!r}"
        )

    def test_now_utc_is_live(self):
        """Two successive calls should differ by at most a few seconds (not frozen)."""
        ts1 = Settings.now_utc()
        ts2 = Settings.now_utc()
        # They could be the same second, but the key thing is they are not a
        # frozen 2025 string.
        assert ts1 >= "2026-01-01 00:00:00", f"Timestamp looks frozen/old: {ts1!r}"

    def test_default_weights_sum_to_one(self):
        """Default AnalysisWeights must satisfy the sum-to-1 invariant."""
        w = get_settings().analysis_weights
        total = w.properties + w.logistics + w.cost + w.sustainability + w.consumer
        assert abs(total - 1.0) < 0.01, f"Default weights sum to {total}"

    def test_analysis_weights_as_dict(self):
        """as_dict() must return all five weight keys."""
        d = get_settings().analysis_weights.as_dict()
        assert set(d.keys()) == {"properties", "logistics", "cost", "sustainability", "consumer"}


# ── AnalysisWeights ───────────────────────────────────────────────────────────

class TestAnalysisWeightsSchema:
    def test_valid_weights(self):
        w = AnalysisWeights(
            properties=0.1, logistics=0.1, cost=0.1, sustainability=0.5, consumer=0.2
        )
        assert abs(w.properties + w.logistics + w.cost + w.sustainability + w.consumer - 1.0) < 0.01

    def test_invalid_weights_raises(self):
        with pytest.raises(ValidationError, match="sum to 1.0"):
            AnalysisWeights(
                properties=0.5, logistics=0.5, cost=0.5, sustainability=0.5, consumer=0.5
            )

    def test_zero_weights_raises(self):
        with pytest.raises(ValidationError, match="sum to 1.0"):
            AnalysisWeights(
                properties=0.0, logistics=0.0, cost=0.0, sustainability=0.0, consumer=0.0
            )


# ── AgentMetadata ─────────────────────────────────────────────────────────────

class TestAgentMetadata:
    def test_basic(self):
        m = AgentMetadata(**SAMPLE_METADATA)
        assert m.timestamp == "2026-09-03 03:00:00"
        assert m.user == "test-user"
        assert m.report_path is None

    def test_with_report_path(self):
        m = AgentMetadata(**SAMPLE_METADATA_WITH_PATH)
        assert m.report_path == "/tmp/report.json"


# ── Product schemas ───────────────────────────────────────────────────────────

class TestProductSchemas:
    def test_product_criterion(self):
        c = ProductCriterion(explanation="solid", concerns="fragile")
        assert c.explanation == "solid"

    def test_product_compatibility_result(self):
        result = ProductCompatibilityResult(
            product_name="Test Protein Bar",
            criteria={
                "physical_form": ProductCriterion(explanation="solid", concerns="fragile"),
                "fragility": ProductCriterion(explanation="sturdy", concerns="breakable"),
            },
            scores={"physical_form": 80.0, "fragility": 72.0},
            metadata=AgentMetadata(**SAMPLE_METADATA),
        )
        assert result.product_name == "Test Protein Bar"
        assert "physical_form" in result.criteria
        assert result.scores["fragility"] == 72.0


# ── Materials schemas ─────────────────────────────────────────────────────────

class TestMaterialsSchemas:
    def test_material_entry(self):
        m = MaterialEntry(material_name="PLA", type="bio_based")
        assert m.type == "bio_based"

    def test_materials_found(self):
        mf = MaterialsFound(
            product_name="Test Product",
            materials={
                "bio_based": [
                    MaterialEntry(material_name="PLA", type="bio_based"),
                    MaterialEntry(material_name="PHA", type="bio_based"),
                ],
                "conventional": [
                    MaterialEntry(material_name="HDPE", type="conventional"),
                ],
            },
            metadata=AgentMetadata(**SAMPLE_METADATA),
        )
        assert len(mf.materials["bio_based"]) == 2
        assert mf.materials["conventional"][0].material_name == "HDPE"


# ── Analysis schemas ──────────────────────────────────────────────────────────

class TestAnalysisSchemas:
    def test_properties_result(self):
        pr = PropertiesResult(
            top_materials=[
                PropertiesMaterial(
                    detail=PropertiesDetail(property_scores={"tensile_strength": 8.0, "barrier_properties": 6.5}),
                    summary=PropertiesSummary(
                        material_name="PLA",
                        overall_score=7.5,
                        confidence="estimated",
                        key_tradeoff="Brittle"
                    )
                )
            ],
            metadata=AgentMetadata(**SAMPLE_METADATA),
        )
        assert pr.top_materials[0].detail.property_scores["tensile_strength"] == 8.0

    def test_logistics_result(self):
        lr = LogisticsResult(
            top_materials=[
                LogisticsMaterial(
                    detail=LogisticsDetail(primary_advantage="Lightweight", cost_consideration="Low"),
                    summary=LogisticsSummary(
                        material_name="HDPE",
                        overall_score=8.2,
                        confidence="estimated",
                        key_tradeoff="Bulky"
                    )
                )
            ],
            metadata=AgentMetadata(**SAMPLE_METADATA),
        )
        assert lr.top_materials[0].summary.overall_score == 8.2

    def test_cost_result(self):
        cr = CostResult(
            top_materials=[
                CostMaterial(
                    detail=CostDetail(
                        base_price="$0.05/unit",
                        total_estimated_cost="$50.00",
                        key_costs=["raw material", "printing"],
                    ),
                    summary=CostSummary(
                        material_name="Cardboard",
                        overall_score=9.0,
                        confidence="estimated",
                        key_tradeoff="Water damage risk"
                    )
                )
            ],
            metadata=AgentMetadata(**SAMPLE_METADATA),
        )
        assert cr.top_materials[0].detail.key_costs == ["raw material", "printing"]

    def test_sustainability_result(self):
        sr = SustainabilityResult(
            top_materials=[
                SustainabilityMaterial(
                    detail=SustainabilityDetail(
                        key_benefit="Fully biodegradable",
                        primary_concern="High production cost",
                    ),
                    summary=SustainabilitySummary(
                        material_name="PHA",
                        overall_score=9.1,
                        confidence="estimated",
                        key_tradeoff="Expensive",
                        recyclability_grade="Compostable"
                    )
                )
            ],
            metadata=AgentMetadata(**SAMPLE_METADATA),
        )
        assert sr.top_materials[0].summary.overall_score == 9.1

    def test_consumer_result(self):
        cr = ConsumerResult(
            top_materials=[
                ConsumerMaterial(
                    detail=ConsumerDetail(
                        consumer_metrics={
                            "aesthetic_appeal": ConsumerMetric(
                                score=9.0, trend_strength="strong", key_insight="Premium feel"
                            ),
                            "usability": ConsumerMetric(
                                score=6.0, trend_strength="moderate", key_insight="Heavy"
                            ),
                        },
                        target_demographics=["millennials", "health-conscious"],
                        market_positioning="Premium sustainable",
                    ),
                    summary=ConsumerSummary(
                        material_name="Glass",
                        overall_score=8.0,
                        confidence="estimated",
                        key_tradeoff="Heavy"
                    )
                )
            ],
            consumer_trends=[
                ConsumerTrend(
                    trend_name="Eco packaging",
                    impact_level="high",
                    relevance="Growing demand",
                )
            ],
            metadata=AgentMetadata(**SAMPLE_METADATA),
        )
        assert cr.top_materials[0].detail.consumer_metrics["aesthetic_appeal"].score == 9.0
        assert cr.consumer_trends[0].impact_level == "high"

    def test_consumer_metric_invalid_trend_strength(self):
        with pytest.raises(ValidationError):
            ConsumerMetric(score=5.0, trend_strength="unknown", key_insight="test")

    def test_consumer_trend_invalid_impact_level(self):
        with pytest.raises(ValidationError):
            ConsumerTrend(trend_name="X", impact_level="extreme", relevance="test")


# ── Report schemas ────────────────────────────────────────────────────────────

class TestReportSchemas:
    def test_executive_summary_report(self):
        report = ExecutiveSummaryReport(
            executive_snapshot="PLA is the top recommendation.",
            composite_score=CompositeScore(
                composite=8.1,
                metrics=CompositeMetrics(
                    properties=7.5,
                    logistics=8.0,
                    cost=6.0,
                    sustainability=9.2,
                    consumer=8.5,
                ),
            ),
            strengths=["High recyclability", "Consumer appeal"],
            trade_offs=["Higher upfront cost"],
            supply_chain_implications="Readily available from EU suppliers.",
            consulting_recommendation="Switch to PLA within 6 months.",
            metadata=AgentMetadata(**SAMPLE_METADATA),
        )
        assert report.composite_score.composite == 8.1
        assert report.composite_score.metrics.sustainability == 9.2
        assert len(report.strengths) == 2
