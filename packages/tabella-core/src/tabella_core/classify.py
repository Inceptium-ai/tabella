"""Auto-classification: suggest PII flags, semantic tags, and a sensitivity
classification for an asset — from field names and (optionally) sampled
content.

Two evidence sources, combined:

1. **Name heuristics** — field-name patterns (email, ssn, dob, mrn, …),
   dependency-free.
2. **Content analysis** — sampled values (via the asset's connector `fetch`)
   run through a `ContentAnalyzer`. The built-in `RegexContentAnalyzer` needs
   no dependencies (regex + Luhn); `PresidioContentAnalyzer` upgrades it to
   NER-grade detection when `presidio-analyzer` is installed (MIT).

Suggestions are proposals, never silent writes — the same rule as discovery.
`apply_suggestions` produces the updated descriptor explicitly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from tabella_core.connectors import get_connector
from tabella_core.models import AssetDescriptor, Classification

# ---------------------------------------------------------------- heuristics

# (name pattern, semantic tag, pii, restricted-grade)
NAME_HINTS: list[tuple[str, str, bool, bool]] = [
    (r"e[-_]?mail", "email", True, False),
    (r"(^|_)(phone|mobile|cell)([_-]?(number|no))?$", "phone", True, False),
    (r"(^|_)ssn$|social[-_]?security", "ssn", True, True),
    (r"(^|_)(first|last|full|middle|sur|given)[-_]?name$", "person_name", True, False),
    (r"(^|_)(dob|date[-_]?of[-_]?birth|birth[-_]?date)$", "date_of_birth", True, True),
    (r"(^|_)mrn$|medical[-_]?record", "medical_record_number", True, True),
    (r"(^|_)(address|street|zip([-_]?code)?|postal[-_]?code)$", "address", True, False),
    (r"credit[-_]?card|card[-_]?(number|no)$|(^|_)pan$", "credit_card", True, True),
    (r"(^|_)ip[-_]?(address|addr)$", "ip_address", True, False),
    (r"passport", "passport", True, True),
    (r"(^|_)iban$|bank[-_]?account|routing[-_]?(number|no)", "bank_account", True, True),
    (r"(^|_)(salary|compensation|wage)s?$", "salary", True, False),
    (r"(^|_)(password|secret|token|api[-_]?key)s?$", "credential", True, True),
    (r"(^|_)(lat|latitude|lon|lng|longitude)$", "geolocation", False, False),
]

# content entity -> (semantic tag, pii, restricted-grade)
ENTITY_HINTS: dict[str, tuple[str, bool, bool]] = {
    "EMAIL_ADDRESS": ("email", True, False),
    "PHONE_NUMBER": ("phone", True, False),
    "US_SSN": ("ssn", True, True),
    "PERSON": ("person_name", True, False),
    "CREDIT_CARD": ("credit_card", True, True),
    "IP_ADDRESS": ("ip_address", True, False),
    "IBAN_CODE": ("bank_account", True, True),
    "US_PASSPORT": ("passport", True, True),
    "LOCATION": ("address", True, False),
}


@dataclass
class FieldSuggestion:
    field: str
    tags: list[str] = field(default_factory=list)
    pii: bool = False
    restricted: bool = False
    evidence: list[dict] = field(default_factory=list)


@dataclass
class AssetClassification:
    asset_id: str
    fields: list[FieldSuggestion]
    suggested_classification: Classification | None  # None = keep current
    sampled_rows: int = 0

    def pii_fields(self) -> list[str]:
        return [f.field for f in self.fields if f.pii]


# ---------------------------------------------------------- content analyzers


class ContentAnalyzer(Protocol):
    """Returns entity hits for a list of values: {entity_name: hit_count}."""

    def analyze_values(self, values: list[str]) -> dict[str, int]: ...


def _luhn_valid(digits: str) -> bool:
    total, parity = 0, len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


class RegexContentAnalyzer:
    """Dependency-free default: regex + checksum detection for the
    highest-signal entities. Presidio replaces this when installed."""

    PATTERNS = {
        "EMAIL_ADDRESS": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$"),
        "US_SSN": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
        "PHONE_NUMBER": re.compile(r"^\+?[\d\s().-]{7,20}$"),
        "IP_ADDRESS": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
    }

    def analyze_values(self, values: list[str]) -> dict[str, int]:
        hits: dict[str, int] = {}
        for value in values:
            text = str(value).strip()
            if not text:
                continue
            for entity, pattern in self.PATTERNS.items():
                if pattern.match(text):
                    # phone must contain enough digits to mean anything
                    if entity == "PHONE_NUMBER" and sum(c.isdigit() for c in text) < 7:
                        continue
                    hits[entity] = hits.get(entity, 0) + 1
            digits = re.sub(r"[\s-]", "", text)
            if digits.isdigit() and 13 <= len(digits) <= 19 and _luhn_valid(digits):
                hits["CREDIT_CARD"] = hits.get("CREDIT_CARD", 0) + 1
        return hits


class PresidioContentAnalyzer:
    """NER-grade detection via presidio-analyzer (optional dependency)."""

    def __init__(self, language: str = "en", score_threshold: float = 0.5):
        from presidio_analyzer import AnalyzerEngine  # noqa: PLC0415 — optional dep

        self._engine = AnalyzerEngine()
        self._language = language
        self._threshold = score_threshold

    def analyze_values(self, values: list[str]) -> dict[str, int]:
        hits: dict[str, int] = {}
        for value in values:
            text = str(value).strip()
            if not text:
                continue
            for result in self._engine.analyze(text=text, language=self._language):
                if result.score >= self._threshold:
                    hits[result.entity_type] = hits.get(result.entity_type, 0) + 1
        return hits


def default_analyzer() -> ContentAnalyzer:
    try:
        return PresidioContentAnalyzer()
    except ImportError:
        return RegexContentAnalyzer()


# -------------------------------------------------------------- classification

MIN_HIT_RATIO = 0.3  # a column is tagged when >=30% of sampled values hit


def classify_asset(
    descriptor: AssetDescriptor,
    *,
    sample_size: int = 50,
    analyzer: ContentAnalyzer | None = None,
    sample_content: bool = True,
) -> AssetClassification:
    suggestions: dict[str, FieldSuggestion] = {}

    def suggest(field_name: str, tag: str, pii: bool, restricted: bool, evidence: dict) -> None:
        entry = suggestions.setdefault(field_name, FieldSuggestion(field=field_name))
        if tag not in entry.tags:
            entry.tags.append(tag)
        entry.pii = entry.pii or pii
        entry.restricted = entry.restricted or restricted
        entry.evidence.append(evidence)

    # 1. name heuristics
    for schema_field in descriptor.asset_schema.fields:
        lowered = schema_field.name.lower()
        for pattern, tag, pii, restricted in NAME_HINTS:
            if re.search(pattern, lowered):
                suggest(
                    schema_field.name,
                    tag,
                    pii,
                    restricted,
                    {"source": "name", "pattern": pattern},
                )

    # 2. content sampling (skipped for non-servable placeholders)
    sampled_rows = 0
    connector = get_connector(descriptor.source.connector)
    if sample_content and connector.introspectable:
        result = connector.fetch(descriptor, limit=sample_size)
        rows = result.records
        sampled_rows = len(rows)
        if rows:
            analyzer = analyzer or default_analyzer()
            for schema_field in descriptor.asset_schema.fields:
                values = [
                    row[schema_field.name] for row in rows if row.get(schema_field.name) is not None
                ]
                if not values:
                    continue
                hits = analyzer.analyze_values([str(v) for v in values])
                for entity, count in hits.items():
                    hint = ENTITY_HINTS.get(entity)
                    if hint is None or count / len(values) < MIN_HIT_RATIO:
                        continue
                    tag, pii, restricted = hint
                    suggest(
                        schema_field.name,
                        tag,
                        pii,
                        restricted,
                        {
                            "source": "content",
                            "entity": entity,
                            "hits": count,
                            "sampled": len(values),
                        },
                    )

    ordered = [suggestions[f.name] for f in descriptor.asset_schema.fields if f.name in suggestions]

    suggested: Classification | None = None
    if any(s.restricted for s in ordered):
        suggested = Classification.restricted
    elif any(s.pii for s in ordered):
        suggested = Classification.confidential
    current_rank = list(Classification).index(descriptor.classification)
    if suggested is not None and list(Classification).index(suggested) <= current_rank:
        suggested = None  # never suggest loosening

    return AssetClassification(
        asset_id=descriptor.id,
        fields=ordered,
        suggested_classification=suggested,
        sampled_rows=sampled_rows,
    )


def apply_suggestions(
    descriptor: AssetDescriptor, classification: AssetClassification
) -> AssetDescriptor:
    """Explicitly apply suggestions to a descriptor (returns the same object)."""
    by_field = {s.field: s for s in classification.fields}
    for schema_field in descriptor.asset_schema.fields:
        suggestion = by_field.get(schema_field.name)
        if suggestion is None:
            continue
        schema_field.pii = schema_field.pii or suggestion.pii
        for tag in suggestion.tags:
            if tag not in schema_field.semantic_tags:
                schema_field.semantic_tags.append(tag)
    if classification.suggested_classification is not None:
        descriptor.classification = classification.suggested_classification
    return descriptor
