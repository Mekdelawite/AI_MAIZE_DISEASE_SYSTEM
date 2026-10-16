"""
=========================================================
Advisor Service Test
=========================================================

Tests the Maize Disease Advisor Service.

Tests:
    1. Advisor initialization
    2. Readiness
    3. Language support
    4. Disease count
    5. English advisory
    6. Amharic advisory
    7. Diagnosis integration
    8. Source information
    9. Validation metadata
    10. Health check

Author : Nigusu Tigabu
Project: AI Maize Disease Detection System
=========================================================
"""

from __future__ import annotations

import json
from pathlib import Path


from ml_model.advisor.advisor_service import AdvisorService
from ml_model.knowledge_base.knowledge_base import KnowledgeBase
# =========================================================
# TEST CONFIGURATION
# =========================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

TEST_IMAGE = (
    PROJECT_ROOT
    / "ml_model"
    / "inference"
    / "test_images"
    / "sample.jpg"
)


# =========================================================
# HELPER
# =========================================================

def print_section(
    title: str,
) -> None:

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# =========================================================
# MAIN TEST
# =========================================================

def main() -> None:

    print("=" * 70)
    print("MAIZE DISEASE ADVISOR SERVICE TEST")
    print("=" * 70)

    # =====================================================
    # TEST 1
    # =====================================================

    print_section(
        "TEST 1 — ADVISOR INITIALIZATION"
    )

    print(
        "Initializing AdvisorService..."
    )

    advisor = AdvisorService()

    print(
        "✓ Advisor service initialized"
    )

    # =====================================================
    # TEST 2
    # =====================================================

    print_section(
        "TEST 2 — READINESS CHECK"
    )

    if not advisor.is_ready():

        raise RuntimeError(
            "Advisor service is not ready."
        )

    print(
        "✓ Advisor service is ready"
    )

    # =====================================================
    # TEST 3
    # =====================================================

    print_section(
        "TEST 3 — LANGUAGE SUPPORT"
    )

    languages = (
        advisor.get_supported_languages()
    )

    print(
        f"Supported languages: {languages}"
    )

    if "en" not in languages:

        raise AssertionError(
            "English language support missing."
        )

    if "am" not in languages:

        raise AssertionError(
            "Amharic language support missing."
        )

    print(
        "✓ English supported"
    )

    print(
        "✓ Amharic supported"
    )

    # =====================================================
    # TEST 4
    # =====================================================

    print_section(
        "TEST 4 — DISEASE COUNT"
    )

    disease_count = (
        advisor.get_disease_count()
    )

    print(
        f"Disease count: {disease_count}"
    )

    if disease_count != 4:

        raise AssertionError(
            f"Expected 4 diseases, got "
            f"{disease_count}"
        )

    print(
        "✓ Correct disease count: 4"
    )

    # =====================================================
    # TEST 5
    # =====================================================

    print_section(
        "TEST 5 — ENGLISH ADVISORY"
    )

    english = (
        advisor.get_advice(
            "Blight",
            "en",
        )
    )

    print(
        f"Disease: {english['disease']}"
    )

    print(
        f"Scientific name: "
        f"{english['scientific_name']}"
    )

    if not english["description"]:

        raise AssertionError(
            "English description is empty."
        )

    if not english["symptoms"]:

        raise AssertionError(
            "English symptoms are empty."
        )

    if not english["prevention"]:

        raise AssertionError(
            "English prevention is empty."
        )

    if not english["management"]:

        raise AssertionError(
            "English management is empty."
        )

    print(
        "✓ English advisory available"
    )

    # =====================================================
    # TEST 6
    # =====================================================

    print_section(
        "TEST 6 — AMHARIC ADVISORY"
    )

    amharic = (
        advisor.get_advice(
            "Blight",
            "am",
        )
    )

    print(
        f"Disease: {amharic['disease']}"
    )

    if not amharic["description"]:

        raise AssertionError(
            "Amharic description is empty."
        )

    if not amharic["symptoms"]:

        raise AssertionError(
            "Amharic symptoms are empty."
        )

    if not amharic["prevention"]:

        raise AssertionError(
            "Amharic prevention is empty."
        )

    if not amharic["management"]:

        raise AssertionError(
            "Amharic management is empty."
        )

    print(
        "✓ Amharic advisory available"
    )

    # =====================================================
    # TEST 7
    # =====================================================

    print_section(
        "TEST 7 — DIAGNOSIS INTEGRATION"
    )

    diagnosis = {

        "prediction": {

            "class_id": 0,

            "class_name": "Blight",

            "display_name": (
                "Northern Leaf Blight"
            ),

            "scientific_name": (
                "Exserohilum turcicum"
            ),

            "confidence": 89.47,
        },

        "top_predictions": [

            {
                "class_id": 0,

                "class_name": "Blight",

                "confidence": 89.47,
            },

            {
                "class_id": 2,

                "class_name": (
                    "Gray_Leaf_Spot"
                ),

                "confidence": 10.42,
            },

            {
                "class_id": 1,

                "class_name": (
                    "Common_Rust"
                ),

                "confidence": 0.11,
            },
        ],
    }

    advisory_result = (
        advisor.advise_from_diagnosis(
            diagnosis,
            language="en",
        )
    )

    if "diagnosis" not in advisory_result:

        raise AssertionError(
            "Diagnosis information missing."
        )

    if "advice" not in advisory_result:

        raise AssertionError(
            "Advice information missing."
        )

    if (
        advisory_result["diagnosis"]
        ["class_name"]
        != "Blight"
    ):

        raise AssertionError(
            "Diagnosis class mismatch."
        )

    print(
        "✓ Diagnosis accepted"
    )

    print(
        "✓ Disease matched with Knowledge Base"
    )

    print(
        "✓ Advisory information generated"
    )

    # =====================================================
    # TEST 8
    # =====================================================

    print_section(
        "TEST 8 — SOURCE INFORMATION"
    )

    sources = (
        advisor.get_sources(
            "Blight"
        )
    )

    print(
        f"Number of sources: "
        f"{len(sources)}"
    )

    if not sources:

        raise AssertionError(
            "No sources found for Blight."
        )

    for source in sources:

        print(
            f"✓ {source.get('organization', '')}"
        )

        print(
            f"  {source.get('title', '')}"
        )

    print(
        "✓ Source information available"
    )

    # =====================================================
    # TEST 9
    # =====================================================

    print_section(
        "TEST 9 — VALIDATION METADATA"
    )

    validation = (
        advisor.get_validation_status(
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

    if "status" not in validation:

        raise AssertionError(
            "Validation status missing."
        )

    print(
        "✓ Validation metadata available"
    )

    # =====================================================
    # TEST 10
    # =====================================================

    print_section(
        "TEST 10 — HEALTH CHECK"
    )

    health = (
        advisor.health_check()
    )

    print(
        json.dumps(
            health,
            indent=4,
            ensure_ascii=False,
        )
    )

    if not health["ready"]:

        raise AssertionError(
            "Health check reports service "
            "not ready."
        )

    print(
        "✓ Advisor health check passed"
    )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    print_section(
        "ALL ADVISOR SERVICE TESTS PASSED"
    )

    print(
        "✓ Advisor initialized"
    )

    print(
        "✓ Knowledge Base connected"
    )

    print(
        "✓ English advisory"
    )

    print(
        "✓ Amharic advisory"
    )

    print(
        "✓ Diagnosis integration"
    )

    print(
        "✓ Source information"
    )

    print(
        "✓ Validation metadata"
    )

    print(
        "✓ Health check"
    )

    print()
    print(
        "AI Maize Disease Advisor is ready "
        "for backend integration."
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()