"""
=========================================================
Knowledge Base Integration Test
=========================================================

Tests the complete bilingual maize disease knowledge
base and validation layer.

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

import json

from knowledge_base import KnowledgeBase
from validators import KnowledgeBaseValidator


def print_section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:

    print("=" * 70)
    print("MAIZE DISEASE KNOWLEDGE BASE TEST")
    print("=" * 70)

    # =====================================================
    # TEST 1 — INITIALIZATION
    # =====================================================

    print_section("TEST 1 — KNOWLEDGE BASE INITIALIZATION")

    print("Initializing KnowledgeBase...")

    knowledge_base = KnowledgeBase()

    print("✓ Knowledge base initialized")

    # =====================================================
    # TEST 2 — READINESS
    # =====================================================

    print_section("TEST 2 — READINESS CHECK")

    assert knowledge_base.is_ready(), (
        "Knowledge base is not ready."
    )

    print("✓ Knowledge base is ready")

    # =====================================================
    # TEST 3 — DISEASE COUNT
    # =====================================================

    print_section("TEST 3 — DISEASE COUNT")

    count = knowledge_base.count()

    print(f"Disease count: {count}")

    assert count == 4, (
        f"Expected 4 diseases, found {count}"
    )

    print("✓ Correct disease count: 4")

    # =====================================================
    # TEST 4 — LANGUAGES
    # =====================================================

    print_section("TEST 4 — LANGUAGE SUPPORT")

    languages = (
        knowledge_base
        .get_supported_languages()
    )

    print(f"Supported languages: {languages}")

    assert "en" in languages

    assert "am" in languages

    print("✓ English supported")

    print("✓ Amharic supported")

    # =====================================================
    # TEST 5 — GET ALL DISEASES
    # =====================================================

    print_section("TEST 5 — DISEASE RECORDS")

    diseases = (
        knowledge_base
        .get_all_diseases()
    )

    for disease in diseases:

        print(
            f"✓ ID {disease.class_id} | "
            f"{disease.class_name}"
        )

    assert len(diseases) == 4

    # =====================================================
    # TEST 6 — LOOKUP BY CLASS NAME
    # =====================================================

    print_section("TEST 6 — LOOKUP BY CLASS NAME")

    disease = (
        knowledge_base
        .get_disease("Blight")
    )

    print(
        f"Class ID : {disease.class_id}"
    )

    print(
        f"Class    : {disease.class_name}"
    )

    print(
        f"English  : {disease.display_name_en}"
    )

    print(
        f"Amharic  : {disease.display_name_am}"
    )

    assert disease.class_id == 0

    assert disease.class_name == "Blight"

    print("✓ Blight lookup successful")

    # =====================================================
    # TEST 7 — LOOKUP BY CLASS ID
    # =====================================================

    print_section("TEST 7 — LOOKUP BY CLASS ID")

    disease = (
        knowledge_base
        .get_disease_by_class_id(0)
    )

    assert disease.class_name == "Blight"

    print(
        f"✓ Class ID 0 → "
        f"{disease.class_name}"
    )

    # =====================================================
    # TEST 8 — ENGLISH INFORMATION
    # =====================================================

    print_section("TEST 8 — ENGLISH INFORMATION")

    english = (
        knowledge_base
        .get_disease_information(
            "Blight",
            "en",
        )
    )

    print(
        f"Disease: "
        f"{english['display_name']}"
    )

    print(
        f"Scientific name: "
        f"{english['scientific_name']}"
    )

    assert english["display_name"]

    assert english["description"]

    assert english["symptoms"]

    assert english["prevention"]

    assert english["management"]

    print("✓ English information available")

    # =====================================================
    # TEST 9 — AMHARIC INFORMATION
    # =====================================================

    print_section("TEST 9 — AMHARIC INFORMATION")

    amharic = (
        knowledge_base
        .get_disease_information(
            "Blight",
            "am",
        )
    )

    print(
        f"Disease: "
        f"{amharic['display_name']}"
    )

    assert amharic["display_name"]

    assert amharic["description"]

    assert amharic["symptoms"]

    assert amharic["prevention"]

    assert amharic["management"]

    print("✓ Amharic information available")

    # =====================================================
    # TEST 10 — ADVISORY CONTENT
    # =====================================================

    print_section("TEST 10 — ADVISORY CONTENT")

    advice = (
        knowledge_base
        .get_advice(
            "Blight",
            "en",
        )
    )

    required_advice_fields = [

        "disease",

        "scientific_name",

        "description",

        "symptoms",

        "causes",

        "favorable_conditions",

        "prevention",

        "management",

        "severity",
    ]

    for field in required_advice_fields:

        assert field in advice, (
            f"Missing advisory field: {field}"
        )

    print("✓ Description available")

    print("✓ Symptoms available")

    print("✓ Causes available")

    print("✓ Favorable conditions available")

    print("✓ Prevention available")

    print("✓ Management available")

    print("✓ Severity available")

    # =====================================================
    # TEST 11 — SOURCES
    # =====================================================

    print_section("TEST 11 — SOURCE INFORMATION")

    sources = (
        knowledge_base
        .get_sources("Blight")
    )

    print(
        f"Number of sources: {len(sources)}"
    )

    assert isinstance(
        sources,
        list,
    )

    assert len(sources) > 0

    for source in sources:

        print(
            f"✓ {source['organization']} "
            f"- {source['title']}"
        )

    print("✓ Source information available")

    # =====================================================
    # TEST 12 — VALIDATION METADATA
    # =====================================================

    print_section("TEST 12 — VALIDATION METADATA")

    validation = (
        knowledge_base
        .get_validation_status(
            "Blight"
        )
    )

    print(
        f"Status: "
        f"{validation['status']}"
    )

    print(
        f"Method: "
        f"{validation['method']}"
    )

    print(
        f"Expert validated: "
        f"{validation['expert_validated']}"
    )

    assert "status" in validation

    assert "method" in validation

    assert "expert_validated" in validation

    print("✓ Validation metadata available")

    # =====================================================
    # TEST 13 — VALIDATOR
    # =====================================================

    print_section("TEST 13 — KNOWLEDGE BASE VALIDATION")

    validator = KnowledgeBaseValidator(
        knowledge_base
    )

    valid = validator.validate(
        raise_on_error=False
    )

    if not valid:

        print()
        print(
            validator.format_errors()
        )

        raise AssertionError(
            "Knowledge base validation failed."
        )

    print("✓ Knowledge base structure is valid")

    # =====================================================
    # WARNINGS
    # =====================================================

    if validator.warnings:

        print()
        print("Validation warnings:")

        print(
            validator.format_warnings()
        )

    else:

        print("✓ No validation warnings")

    # =====================================================
    # TEST 14 — VALIDATION REPORT
    # =====================================================

    print_section("TEST 14 — VALIDATION REPORT")

    report = (
        validator.get_report()
    )

    print(
        json.dumps(
            report,
            indent=4,
            ensure_ascii=False,
        )
    )

    assert report["valid"] is True

    assert report["disease_count"] == 4

    assert "en" in (
        report["supported_languages"]
    )

    assert "am" in (
        report["supported_languages"]
    )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    print()
    print("=" * 70)
    print("ALL KNOWLEDGE BASE TESTS PASSED")
    print("=" * 70)

    print()
    print("✓ Knowledge base loaded")
    print("✓ 4 disease records available")
    print("✓ English support")
    print("✓ Amharic support")
    print("✓ Disease lookup")
    print("✓ Class ID lookup")
    print("✓ Disease information")
    print("✓ Advisory content")
    print("✓ Source information")
    print("✓ Validation metadata")
    print("✓ Knowledge base validation")
    print()
    print(
        "Knowledge Base is ready for Advisor integration."
    )
    print()


if __name__ == "__main__":
    main()