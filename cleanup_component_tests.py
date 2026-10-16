"""
=========================================================
Cleanup Component 4 and Component 5 Test Records
=========================================================

Deletes ONLY records explicitly created by the
Component 4 and Component 5 tests.

IMPORTANT:
- Does not delete real application records.
- Component 4 artifacts are identified by source
  "component4_test".
- Component 5 artifacts are identified by the
  diagnosis IDs created by the tests.
=========================================================
"""

from backend.app.main import create_app
from backend.app.extensions import db
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.advisory_record import AdvisoryRecord


# ---------------------------------------------------------
# KNOWN TEST ARTIFACTS
# ---------------------------------------------------------

COMPONENT_4_DIAGNOSIS_IDS = {
    111,
}

COMPONENT_4_ADVISORY_SOURCE = "component4_test"

COMPONENT_5_DIAGNOSIS_IDS = {
    113,
    115,
    116,
}


# ---------------------------------------------------------
# APPLICATION
# ---------------------------------------------------------

app = create_app()


with app.app_context():

    print("=" * 60)
    print("CLEANUP COMPONENT 4 + COMPONENT 5 TEST RECORDS")
    print("=" * 60)

    # -----------------------------------------------------
    # FIND COMPONENT 4 ADVISORIES
    # -----------------------------------------------------

    component4_advisories = (
        AdvisoryRecord.query
        .filter(
            AdvisoryRecord.source == COMPONENT_4_ADVISORY_SOURCE
        )
        .all()
    )

    # -----------------------------------------------------
    # FIND COMPONENT 5 DIAGNOSES
    # -----------------------------------------------------

    component5_diagnoses = (
        DiagnosisRecord.query
        .filter(
            DiagnosisRecord.id.in_(COMPONENT_5_DIAGNOSIS_IDS)
        )
        .all()
    )

    # -----------------------------------------------------
    # FIND COMPONENT 4 DIAGNOSES
    # -----------------------------------------------------

    component4_diagnoses = (
        DiagnosisRecord.query
        .filter(
            DiagnosisRecord.id.in_(COMPONENT_4_DIAGNOSIS_IDS)
        )
        .all()
    )

    # -----------------------------------------------------
    # DISPLAY WHAT WILL BE DELETED
    # -----------------------------------------------------

    print("\nComponent 4 advisories:")
    for record in component4_advisories:
        print(
            f"  Advisory ID={record.id}, "
            f"diagnosis_id={record.diagnosis_id}, "
            f"source={record.source!r}"
        )

    print("\nComponent 4 diagnoses:")
    for record in component4_diagnoses:
        print(
            f"  Diagnosis ID={record.id}, "
            f"user_id={record.user_id}, "
            f"disease={record.disease_class}"
        )

    print("\nComponent 5 diagnoses:")
    for record in component5_diagnoses:
        print(
            f"  Diagnosis ID={record.id}, "
            f"user_id={record.user_id}, "
            f"disease={record.disease_class}"
        )

    # -----------------------------------------------------
    # SAFETY CHECK
    # -----------------------------------------------------

    print("\nRecords selected for cleanup:")
    print(
        f"  Component 4 diagnoses: "
        f"{len(component4_diagnoses)}"
    )
    print(
        f"  Component 4 advisories: "
        f"{len(component4_advisories)}"
    )
    print(
        f"  Component 5 diagnoses: "
        f"{len(component5_diagnoses)}"
    )

    # -----------------------------------------------------
    # DELETE DIAGNOSES FIRST
    #
    # Linked advisories should cascade through the FK.
    # -----------------------------------------------------

    for record in component5_diagnoses:
        db.session.delete(record)

    for record in component4_diagnoses:
        db.session.delete(record)

    db.session.flush()

    # -----------------------------------------------------
    # DELETE REMAINING COMPONENT 4 ORPHAN ADVISORIES
    #
    # This catches advisory 59, which has no diagnosis_id.
    # -----------------------------------------------------

    remaining_component4_advisories = (
        AdvisoryRecord.query
        .filter(
            AdvisoryRecord.source == COMPONENT_4_ADVISORY_SOURCE
        )
        .all()
    )

    for record in remaining_component4_advisories:
        db.session.delete(record)

    # -----------------------------------------------------
    # COMMIT
    # -----------------------------------------------------

    db.session.commit()

    # -----------------------------------------------------
    # VERIFY
    # -----------------------------------------------------

    remaining_component4_diagnoses = (
        DiagnosisRecord.query
        .filter(
            DiagnosisRecord.id.in_(COMPONENT_4_DIAGNOSIS_IDS)
        )
        .all()
    )

    remaining_component5_diagnoses = (
        DiagnosisRecord.query
        .filter(
            DiagnosisRecord.id.in_(COMPONENT_5_DIAGNOSIS_IDS)
        )
        .all()
    )

    remaining_component4_advisories = (
        AdvisoryRecord.query
        .filter(
            AdvisoryRecord.source == COMPONENT_4_ADVISORY_SOURCE
        )
        .all()
    )

    print("\nVerification:")
    print(
        f"  Component 4 diagnoses remaining: "
        f"{len(remaining_component4_diagnoses)}"
    )
    print(
        f"  Component 5 diagnoses remaining: "
        f"{len(remaining_component5_diagnoses)}"
    )
    print(
        f"  Component 4 advisories remaining: "
        f"{len(remaining_component4_advisories)}"
    )

    if (
        not remaining_component4_diagnoses
        and not remaining_component5_diagnoses
        and not remaining_component4_advisories
    ):
        print("\n" + "=" * 60)
        print("CLEANUP PASSED")
        print("=" * 60)
    else:
        print("\nWARNING: Some test records still remain.")