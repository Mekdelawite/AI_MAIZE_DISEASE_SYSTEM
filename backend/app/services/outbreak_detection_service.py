"""
=========================================================
Outbreak Detection Service
=========================================================

Detects and evaluates maize disease outbreak risk using
diagnosis, farmer, geographic, and temporal information.

Current risk components:

    1. Incidence
    2. Case concentration
    3. Recent disease activity
    4. Geographic spread

The service produces:

    - outbreak_risk_score: 0-100
    - risk_level: low/moderate/high/critical
    - alert_required: True/False

IMPORTANT:

    Outbreak risk is different from:

        - AI prediction confidence
        - Individual plant disease severity

The current implementation is intentionally conservative
when the available population/sample size is small.

Future components:

    - Weather/environmental risk
    - Disease-specific epidemiological parameters
    - Crop/field severity
    - Disease progression
    - More advanced spatial analysis
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from backend.app.extensions import db
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.user import User


class OutbreakDetectionService:
    """
    Service responsible for detecting and evaluating
    geographic maize disease outbreaks.
    """

    # =====================================================
    # SCORE WEIGHTS
    # =====================================================

    INCIDENCE_WEIGHT = 0.35
    CASE_CONCENTRATION_WEIGHT = 0.15
    RECENCY_WEIGHT = 0.20
    GEOGRAPHIC_SPREAD_WEIGHT = 0.30

    # =====================================================
    # RISK THRESHOLDS
    # =====================================================

    LOW_MAX = 24
    MODERATE_MAX = 49
    HIGH_MAX = 74

    # =====================================================
    # MINIMUM EVIDENCE
    # =====================================================

    # Minimum number of registered farmers required before
    # incidence can strongly influence outbreak classification.

    MIN_FARMERS_FOR_OUTBREAK = 5

    # Minimum affected farmers for an outbreak alert.

    MIN_AFFECTED_FARMERS_FOR_ALERT = 2

    # Minimum affected Kebeles for geographic spread to
    # become meaningful.

    MIN_AFFECTED_KEBELES_FOR_SPREAD = 2

    # =====================================================
    # BASIC HELPERS
    # =====================================================

    @staticmethod
    def _clamp(
        value: float,
        minimum: float = 0.0,
        maximum: float = 100.0,
    ) -> float:
        """
        Keep a value between minimum and maximum.
        """

        return max(
            minimum,
            min(value, maximum),
        )

    # =====================================================
    # REGISTERED FARMERS
    # =====================================================

    @staticmethod
    def count_registered_farmers(
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
    ) -> int:
        """
        Count active registered farmers in the requested
        geographic area.
        """

        query = (
            db.session.query(
                func.count(User.id)
            )
            .join(
                FarmerProfile,
                FarmerProfile.user_id == User.id,
            )
            .filter(
                User.role == "farmer",
                User.is_active.is_(True),
                FarmerProfile.region == region,
            )
        )

        if woreda is not None:
            query = query.filter(
                FarmerProfile.woreda == woreda
            )

        if kebele is not None:
            query = query.filter(
                FarmerProfile.kebele == kebele
            )

        return int(
            query.scalar() or 0
        )

    # =====================================================
    # DISEASE CASE AGGREGATION
    # =====================================================

    @staticmethod
    def count_disease_cases(
        disease_class: str,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
        days: int = 7,
    ) -> dict:
        """
        Count total disease diagnoses and unique affected
        farmers in an area during the selected period.
        """

        if days <= 0:
            raise ValueError(
                "days must be greater than zero"
            )

        now = datetime.now(timezone.utc)

        start_time = (
            now - timedelta(days=days)
        )

        query = (
            db.session.query(
                func.count(
                    DiagnosisRecord.id
                ),
                func.count(
                    func.distinct(
                        DiagnosisRecord.user_id
                    )
                ),
            )
            .select_from(
                DiagnosisRecord
            )
            .join(
                User,
                DiagnosisRecord.user_id == User.id,
            )
            .join(
                FarmerProfile,
                FarmerProfile.user_id == User.id,
            )
            .filter(
                DiagnosisRecord.disease_class
                == disease_class,

                DiagnosisRecord.created_at
                >= start_time,

                User.role == "farmer",

                User.is_active.is_(True),

                FarmerProfile.region
                == region,
            )
        )

        if woreda is not None:
            query = query.filter(
                FarmerProfile.woreda
                == woreda
            )

        if kebele is not None:
            query = query.filter(
                FarmerProfile.kebele
                == kebele
            )

        (
            total_diagnoses,
            unique_farmers,
        ) = query.one()

        return {
            "disease_class": disease_class,
            "region": region,
            "woreda": woreda,
            "kebele": kebele,
            "days": days,
            "total_diagnoses": int(
                total_diagnoses or 0
            ),
            "unique_farmers": int(
                unique_farmers or 0
            ),
        }

    # =====================================================
    # RECENT DISEASE CASES
    # =====================================================

    @staticmethod
    def count_recent_cases(
        disease_class: str,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
        recent_days: int = 2,
    ) -> int:
        """
        Count disease diagnoses occurring during the most
        recent period.
        """

        if recent_days <= 0:
            raise ValueError(
                "recent_days must be greater than zero"
            )

        now = datetime.now(timezone.utc)

        start_time = (
            now - timedelta(days=recent_days)
        )

        query = (
            db.session.query(
                func.count(
                    DiagnosisRecord.id
                )
            )
            .select_from(
                DiagnosisRecord
            )
            .join(
                User,
                DiagnosisRecord.user_id == User.id,
            )
            .join(
                FarmerProfile,
                FarmerProfile.user_id == User.id,
            )
            .filter(
                DiagnosisRecord.disease_class
                == disease_class,

                DiagnosisRecord.created_at
                >= start_time,

                User.role == "farmer",

                User.is_active.is_(True),

                FarmerProfile.region
                == region,
            )
        )

        if woreda is not None:
            query = query.filter(
                FarmerProfile.woreda
                == woreda
            )

        if kebele is not None:
            query = query.filter(
                FarmerProfile.kebele
                == kebele
            )

        return int(
            query.scalar() or 0
        )

    # =====================================================
    # TOTAL KEBELES
    # =====================================================

    @staticmethod
    def count_total_kebeles(
        region: str,
        woreda: str | None = None,
    ) -> int:
        """
        Count distinct registered Kebeles in an area.
        """

        query = (
            db.session.query(
                func.count(
                    func.distinct(
                        FarmerProfile.kebele
                    )
                )
            )
            .select_from(
                FarmerProfile
            )
            .join(
                User,
                FarmerProfile.user_id == User.id,
            )
            .filter(
                User.role == "farmer",
                User.is_active.is_(True),
                FarmerProfile.region == region,
                FarmerProfile.kebele.isnot(None),
            )
        )

        if woreda is not None:
            query = query.filter(
                FarmerProfile.woreda
                == woreda
            )

        return int(
            query.scalar() or 0
        )

    # =====================================================
    # AFFECTED KEBELES
    # =====================================================

    @staticmethod
    def count_affected_kebeles(
        disease_class: str,
        region: str,
        woreda: str | None = None,
        days: int = 7,
    ) -> int:
        """
        Count distinct Kebeles where the disease has been
        diagnosed during the selected period.
        """

        if days <= 0:
            raise ValueError(
                "days must be greater than zero"
            )

        now = datetime.now(timezone.utc)

        start_time = (
            now - timedelta(days=days)
        )

        # IMPORTANT:
        #
        # DiagnosisRecord must be the starting table.
        #
        # Previous implementation accidentally generated:
        #
        # farmer_profiles
        # JOIN users ON diagnosis_records...
        #
        # before diagnosis_records was in FROM.
        #
        # select_from(DiagnosisRecord) fixes that.

        query = (
            db.session.query(
                func.count(
                    func.distinct(
                        FarmerProfile.kebele
                    )
                )
            )
            .select_from(
                DiagnosisRecord
            )
            .join(
                User,
                DiagnosisRecord.user_id
                == User.id,
            )
            .join(
                FarmerProfile,
                FarmerProfile.user_id
                == User.id,
            )
            .filter(
                DiagnosisRecord.disease_class
                == disease_class,

                DiagnosisRecord.created_at
                >= start_time,

                User.role == "farmer",

                User.is_active.is_(True),

                FarmerProfile.region
                == region,

                FarmerProfile.kebele.isnot(None),
            )
        )

        if woreda is not None:
            query = query.filter(
                FarmerProfile.woreda
                == woreda
            )

        return int(
            query.scalar() or 0
        )

    # =====================================================
    # INCIDENCE SCORE
    # =====================================================

    @classmethod
    def calculate_incidence_score(
        cls,
        affected_farmers: int,
        registered_farmers: int,
    ) -> float:
        """
        Calculate disease incidence.

        Formula:

            affected farmers
            ----------------- × 100
            registered farmers

        NOTE:

        The raw incidence is returned here.

        The final outbreak classification applies minimum
        evidence rules separately.
        """

        if registered_farmers <= 0:
            return 0.0

        incidence = (
            affected_farmers
            / registered_farmers
        ) * 100

        return round(
            cls._clamp(incidence),
            2,
        )

    # =====================================================
    # CASE CONCENTRATION
    # =====================================================

    @classmethod
    def calculate_case_concentration_score(
        cls,
        total_diagnoses: int,
        registered_farmers: int,
    ) -> float:
        """
        Calculate diagnosis concentration relative to
        registered farmers.

        This metric has a lower weight because repeated
        diagnoses may come from the same farmer.
        """

        if registered_farmers <= 0:
            return 0.0

        concentration = (
            total_diagnoses
            / registered_farmers
        ) * 100

        return round(
            cls._clamp(concentration),
            2,
        )

    # =====================================================
    # RECENCY SCORE
    # =====================================================

    @classmethod
    def calculate_recency_score(
        cls,
        total_diagnoses: int,
        recent_diagnoses: int,
    ) -> float:
        """
        Measure how concentrated cases are in the recent
        period.
        """

        if total_diagnoses <= 0:
            return 0.0

        recency = (
            recent_diagnoses
            / total_diagnoses
        ) * 100

        return round(
            cls._clamp(recency),
            2,
        )

    # =====================================================
    # GEOGRAPHIC SPREAD SCORE
    # =====================================================

    @classmethod
    def calculate_geographic_spread_score(
        cls,
        affected_kebeles: int,
        total_kebeles: int,
    ) -> float:
        """
        Calculate geographic disease spread.

        Formula:

            affected Kebeles
            ---------------- × 100
            total Kebeles

        Geographic spread is only meaningful when at least
        two Kebeles are affected.
        """

        if total_kebeles <= 0:
            return 0.0

        if affected_kebeles < (
            cls.MIN_AFFECTED_KEBELES_FOR_SPREAD
        ):
            return 0.0

        spread = (
            affected_kebeles
            / total_kebeles
        ) * 100

        return round(
            cls._clamp(spread),
            2,
        )

    # =====================================================
    # FINAL OUTBREAK SCORE
    # =====================================================

    @classmethod
    def calculate_outbreak_score(
        cls,
        incidence_score: float,
        case_concentration_score: float,
        recency_score: float,
        geographic_spread_score: float,
        registered_farmers: int = 0,
        affected_farmers: int = 0,
    ) -> float:
        """
        Calculate final outbreak risk score.

        Components:

            Incidence           35%
            Case concentration  15%
            Recency             20%
            Geographic spread   30%

        Small populations are handled conservatively.

        If there are not enough registered farmers or
        affected farmers, the final score is capped.
        """

        score = (
            incidence_score
            * cls.INCIDENCE_WEIGHT

            + case_concentration_score
            * cls.CASE_CONCENTRATION_WEIGHT

            + recency_score
            * cls.RECENCY_WEIGHT

            + geographic_spread_score
            * cls.GEOGRAPHIC_SPREAD_WEIGHT
        )

        score = cls._clamp(score)

        # ---------------------------------------------
        # Small population protection
        # ---------------------------------------------

        if registered_farmers < (
            cls.MIN_FARMERS_FOR_OUTBREAK
        ):
            score = min(score, 24.0)

        # ---------------------------------------------
        # Single affected farmer protection
        # ---------------------------------------------

        if affected_farmers < (
            cls.MIN_AFFECTED_FARMERS_FOR_ALERT
        ):
            score = min(score, 24.0)

        return round(
            score,
            2,
        )

    # =====================================================
    # RISK LEVEL
    # =====================================================

    @classmethod
    def calculate_risk_level(
        cls,
        outbreak_score: float,
    ) -> str:
        """
        Convert 0-100 outbreak score into a risk level.
        """

        if outbreak_score <= cls.LOW_MAX:
            return "low"

        if outbreak_score <= cls.MODERATE_MAX:
            return "moderate"

        if outbreak_score <= cls.HIGH_MAX:
            return "high"

        return "critical"

    # =====================================================
    # ALERT DECISION
    # =====================================================

    @classmethod
    def should_send_alert(
        cls,
        risk_level: str,
        affected_farmers: int = 0,
        registered_farmers: int = 0,
    ) -> bool:
        """
        Determine whether an automatic outbreak alert
        should be sent.

        An alert requires:

            1. Moderate or higher risk
            2. Minimum affected farmers
            3. Minimum registered population
        """

        if risk_level not in {
            "moderate",
            "high",
            "critical",
        }:
            return False

        if affected_farmers < (
            cls.MIN_AFFECTED_FARMERS_FOR_ALERT
        ):
            return False

        if registered_farmers < (
            cls.MIN_FARMERS_FOR_OUTBREAK
        ):
            return False

        return True

    # =====================================================
    # COMPLETE AREA ANALYSIS
    # =====================================================

    @classmethod
    def analyze_area(
        cls,
        disease_class: str,
        region: str,
        woreda: str | None = None,
        kebele: str | None = None,
        days: int = 7,
        recent_days: int = 2,
    ) -> dict:
        """
        Perform complete outbreak analysis.

        Supported levels:

            Region
            Region + Woreda
            Region + Woreda + Kebele
        """

        if days <= 0:
            raise ValueError(
                "days must be greater than zero"
            )

        if recent_days <= 0:
            raise ValueError(
                "recent_days must be greater than zero"
            )

        if recent_days > days:
            raise ValueError(
                "recent_days cannot be greater than days"
            )

        # =================================================
        # 1. DISEASE CASES
        # =================================================

        disease_data = (
            cls.count_disease_cases(
                disease_class=disease_class,
                region=region,
                woreda=woreda,
                kebele=kebele,
                days=days,
            )
        )

        # =================================================
        # 2. REGISTERED FARMERS
        # =================================================

        registered_farmers = (
            cls.count_registered_farmers(
                region=region,
                woreda=woreda,
                kebele=kebele,
            )
        )

        # =================================================
        # 3. RECENT CASES
        # =================================================

        recent_diagnoses = (
            cls.count_recent_cases(
                disease_class=disease_class,
                region=region,
                woreda=woreda,
                kebele=kebele,
                recent_days=recent_days,
            )
        )

        # =================================================
        # 4. INCIDENCE
        # =================================================

        incidence_score = (
            cls.calculate_incidence_score(
                affected_farmers=(
                    disease_data[
                        "unique_farmers"
                    ]
                ),
                registered_farmers=(
                    registered_farmers
                ),
            )
        )

        # =================================================
        # 5. CASE CONCENTRATION
        # =================================================

        case_concentration_score = (
            cls.calculate_case_concentration_score(
                total_diagnoses=(
                    disease_data[
                        "total_diagnoses"
                    ]
                ),
                registered_farmers=(
                    registered_farmers
                ),
            )
        )

        # =================================================
        # 6. RECENCY
        # =================================================

        recency_score = (
            cls.calculate_recency_score(
                total_diagnoses=(
                    disease_data[
                        "total_diagnoses"
                    ]
                ),
                recent_diagnoses=(
                    recent_diagnoses
                ),
            )
        )

        # =================================================
        # 7. GEOGRAPHIC SPREAD
        # =================================================

        if kebele is None:

            total_kebeles = (
                cls.count_total_kebeles(
                    region=region,
                    woreda=woreda,
                )
            )

            affected_kebeles = (
                cls.count_affected_kebeles(
                    disease_class=disease_class,
                    region=region,
                    woreda=woreda,
                    days=days,
                )
            )

            geographic_spread_score = (
                cls.calculate_geographic_spread_score(
                    affected_kebeles=(
                        affected_kebeles
                    ),
                    total_kebeles=(
                        total_kebeles
                    ),
                )
            )

        else:

            # No smaller geographic unit currently exists
            # below Kebele.

            total_kebeles = 1

            affected_kebeles = (
                1
                if disease_data[
                    "total_diagnoses"
                ] > 0
                else 0
            )

            geographic_spread_score = 0.0

        # =================================================
        # 8. FINAL SCORE
        # =================================================

        outbreak_score = (
            cls.calculate_outbreak_score(
                incidence_score=(
                    incidence_score
                ),
                case_concentration_score=(
                    case_concentration_score
                ),
                recency_score=(
                    recency_score
                ),
                geographic_spread_score=(
                    geographic_spread_score
                ),
                registered_farmers=(
                    registered_farmers
                ),
                affected_farmers=(
                    disease_data[
                        "unique_farmers"
                    ]
                ),
            )
        )

        # =================================================
        # 9. RISK LEVEL
        # =================================================

        risk_level = (
            cls.calculate_risk_level(
                outbreak_score
            )
        )

        # =================================================
        # 10. ALERT DECISION
        # =================================================

        alert_required = (
            cls.should_send_alert(
                risk_level=risk_level,
                affected_farmers=(
                    disease_data[
                        "unique_farmers"
                    ]
                ),
                registered_farmers=(
                    registered_farmers
                ),
            )
        )

        # =================================================
        # 11. FINAL RESULT
        # =================================================

        return {
            # ---------------------------------------------
            # Disease
            # ---------------------------------------------

            "disease_class": disease_class,

            # ---------------------------------------------
            # Geographic information
            # ---------------------------------------------

            "region": region,
            "woreda": woreda,
            "kebele": kebele,

            # ---------------------------------------------
            # Time periods
            # ---------------------------------------------

            "analysis_period_days": days,
            "recent_period_days": recent_days,

            # ---------------------------------------------
            # Farmer statistics
            # ---------------------------------------------

            "registered_farmers": (
                registered_farmers
            ),

            "affected_farmers": (
                disease_data[
                    "unique_farmers"
                ]
            ),

            # ---------------------------------------------
            # Disease statistics
            # ---------------------------------------------

            "total_diagnoses": (
                disease_data[
                    "total_diagnoses"
                ]
            ),

            "recent_diagnoses": (
                recent_diagnoses
            ),

            # ---------------------------------------------
            # Geographic statistics
            # ---------------------------------------------

            "total_kebeles": (
                total_kebeles
            ),

            "affected_kebeles": (
                affected_kebeles
            ),

            # ---------------------------------------------
            # Component scores
            # ---------------------------------------------

            "incidence_score": (
                incidence_score
            ),

            "case_concentration_score": (
                case_concentration_score
            ),

            "recency_score": (
                recency_score
            ),

            "geographic_spread_score": (
                geographic_spread_score
            ),

            # ---------------------------------------------
            # Final outbreak assessment
            # ---------------------------------------------

            "outbreak_risk_score": (
                outbreak_score
            ),

            "risk_level": risk_level,

            "alert_required": (
                alert_required
            ),
        }