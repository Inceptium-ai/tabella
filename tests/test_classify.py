"""Auto-classification: name heuristics, content analyzers, apply semantics."""

from tabella_core.classify import (
    AssetClassification,
    RegexContentAnalyzer,
    apply_suggestions,
    classify_asset,
)
from tabella_core.models import Classification
from tabella_core.pipeline import register


def _descriptor(tmp_path, manifest):
    return register(manifest, tmp_path / "catalog").descriptor


def test_name_and_content_detection_on_real_sqlite(tmp_path, customers_manifest):
    # strip the declared contract so detection, not declarations, does the work
    customers_manifest.contract.fields = []
    descriptor = _descriptor(tmp_path, customers_manifest)
    for schema_field in descriptor.asset_schema.fields:
        schema_field.pii = False

    result = classify_asset(descriptor)
    by_field = {s.field: s for s in result.fields}

    email = by_field["email"]
    assert "email" in email.tags
    assert email.pii is True
    sources = {e["source"] for e in email.evidence}
    assert sources == {"name", "content"}  # both the column name AND the values hit

    assert "person_name" in by_field["full_name"].tags
    assert result.sampled_rows == 3
    assert result.suggested_classification is Classification.confidential


def test_restricted_grade_signals_win():
    analyzer = RegexContentAnalyzer()
    hits = analyzer.analyze_values(["123-45-6789", "078-05-1120"])
    assert hits["US_SSN"] == 2
    # Luhn-valid card number (standard test number)
    assert analyzer.analyze_values(["4111 1111 1111 1111"])["CREDIT_CARD"] == 1
    # Luhn-invalid digits are not cards
    assert "CREDIT_CARD" not in analyzer.analyze_values(["4111 1111 1111 1112"])


def test_names_only_for_placeholder_assets(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    # placeholder sources (api) can't be sampled — name heuristics still run
    descriptor.source.connector = "api"
    result = classify_asset(descriptor)
    assert result.sampled_rows == 0
    assert any("email" in s.tags for s in result.fields)


def test_never_suggests_loosening(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)
    descriptor.classification = Classification.restricted
    result = classify_asset(descriptor, sample_content=False)
    assert result.suggested_classification is None  # confidential < restricted


def test_injected_analyzer_and_hit_ratio(tmp_path, customers_manifest):
    descriptor = _descriptor(tmp_path, customers_manifest)

    class OneHitAnalyzer:
        def analyze_values(self, values):
            return {"US_SSN": 1}  # 1 of 3 sampled -> below the 30%... = 33%, above

    result = classify_asset(descriptor, analyzer=OneHitAnalyzer())
    assert any("ssn" in s.tags for s in result.fields)

    class NoiseAnalyzer:
        def analyze_values(self, values):
            return {"US_SSN": 0}

    result = classify_asset(descriptor, analyzer=NoiseAnalyzer())
    assert not any("ssn" in s.tags for s in result.fields)


def test_apply_suggestions_is_explicit_and_additive(tmp_path, customers_manifest):
    customers_manifest.contract.fields = []
    descriptor = _descriptor(tmp_path, customers_manifest)
    for schema_field in descriptor.asset_schema.fields:
        schema_field.pii = False

    result = classify_asset(descriptor)
    assert descriptor.asset_schema.field("email").pii is False  # nothing applied yet

    apply_suggestions(descriptor, result)
    email = descriptor.asset_schema.field("email")
    assert email.pii is True
    assert "email" in email.semantic_tags
    assert descriptor.classification is Classification.confidential

    # idempotent re-apply
    apply_suggestions(descriptor, result)
    assert email.semantic_tags.count("email") == 1


def test_empty_suggestion_shape():
    empty = AssetClassification(asset_id="x", fields=[], suggested_classification=None)
    assert empty.pii_fields() == []
