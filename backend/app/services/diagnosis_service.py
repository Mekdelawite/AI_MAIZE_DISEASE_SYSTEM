
"""
=========================================================
Diagnosis Integration Service
=========================================================

Connects the ML diagnosis service with the backend
database and asynchronous outbreak evaluation.

Architecture
------------

    Farmer uploads image
            |
            v
      ML Diagnosis
            |
            v
    Save DiagnosisRecord
            |
            v
    Queue Outbreak Job
            |
            +---------------------> Background Thread
            |                              |
            v                              v
    Return diagnosis                 OutbreakJobService
    immediately                           |
                                          v
                                  OutbreakAlertService
                                          |
                                          v
                                    Alert / SMS

Important
---------
Outbreak analysis MUST NOT block the farmer's diagnosis
response.

The diagnosis is saved and returned first. Outbreak
processing happens asynchronously after the database
record has been committed.

=========================================================
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from flask import current_app

from backend.app.extensions import db
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.services.outbreak_job_service import OutbreakJobService
from backend.app.services.database_retry_service import (
    DatabaseRetryService,
)


# =========================================================
# EXCEPTIONS
# =========================================================

class DiagnosisIntegrationError(Exception):
    """
    Base exception for diagnosis integration errors.
    """


# ---------------------------------------------------------
# Backward-compatible exception name
# ---------------------------------------------------------
#
# Existing routes may already import:
#
#     BackendDiagnosisError
#
# Keep this alias so existing backend code does not break.
#
BackendDiagnosisError = DiagnosisIntegrationError


# =========================================================
# SERVICE
# =========================================================

class DiagnosisIntegrationService:
    """
    Integration layer between the ML diagnosis service,
    PostgreSQL database, and asynchronous outbreak
    processing.

    Responsibilities
    ----------------
    - Initialize ML DiagnosisService
    - Check ML service readiness
    - Validate uploaded image
    - Run AI diagnosis
    - Save diagnosis result
    - Associate diagnosis with authenticated user
    - Queue outbreak evaluation asynchronously
    - Return diagnosis immediately
    """

    # =====================================================
    # INITIALIZATION
    # =====================================================

    def __init__(self) -> None:
        """
        Initialize the diagnosis integration service.
        """

        self._diagnosis_service: Any = None

        self._initialize()

    # =====================================================
    # ML SERVICE INITIALIZATION
    # =====================================================

    def _initialize(self) -> None:
        """
        Initialize the existing ML DiagnosisService.

        The ML service is imported lazily so that importing
        the backend service does not unnecessarily create
        circular imports during Flask startup.
        """

        try:
            from ml_model.ai_service.diagnosis_service import (
                DiagnosisService,
            )

            self._diagnosis_service = DiagnosisService()

        except Exception as error:
            self._diagnosis_service = None

            print(
                "[DIAGNOSIS SERVICE] Initialization failed:",
                error,
            )

    # =====================================================
    # READINESS
    # =====================================================

    def is_ready(self) -> bool:
        """
        Return True when the underlying ML service is ready.
        """

        if self._diagnosis_service is None:
            return False

        try:
            # If the underlying service provides is_ready(),
            # use it.
            if hasattr(
                self._diagnosis_service,
                "is_ready",
            ):
                return bool(
                    self._diagnosis_service.is_ready()
                )

            # Fallback for a service that does not expose
            # is_ready().
            return True

        except Exception as error:
            print(
                "[DIAGNOSIS SERVICE] Readiness check failed:",
                error,
            )
            return False

    # =====================================================
    # BACKGROUND OUTBREAK JOB
    # =====================================================

    @staticmethod
    def _run_outbreak_job(
        app: Any,
        diagnosis_id: int,
    ) -> None:
        """
        Execute outbreak processing in a background thread.

        A new Flask application context is created inside the
        thread because Flask-SQLAlchemy requires an active
        application context.

        Only primitive data is passed between threads:

            - Flask app object
            - diagnosis ID

        ORM objects and SQLAlchemy sessions are NOT shared
        between threads.
        """

        try:
            with app.app_context():

                print(
                    f"[OUTBREAK JOB] Starting diagnosis "
                    f"{diagnosis_id}"
                )

                job_service = OutbreakJobService()

                result = job_service.process_diagnosis(
                    diagnosis_id
                )

                print(
                    f"[OUTBREAK JOB] Completed diagnosis "
                    f"{diagnosis_id}:",
                    result,
                )

        except Exception as error:

            print(
                f"[OUTBREAK JOB] Failed for diagnosis "
                f"{diagnosis_id}:",
                error,
            )

            # Make sure the background thread does not leave
            # a broken SQLAlchemy transaction behind.
            try:
                with app.app_context():
                    db.session.rollback()

            except Exception:
                pass

        finally:

            # Remove the thread-local SQLAlchemy session.
            try:
                with app.app_context():
                    db.session.remove()

            except Exception:
                pass

    # =====================================================
    # QUEUE OUTBREAK JOB
    # =====================================================

    def _queue_outbreak_job(
        self,
        diagnosis_id: int,
    ) -> dict[str, Any]:
        """
        Queue asynchronous outbreak processing.

        This method ONLY starts the background thread.
        It does not perform outbreak analysis itself.

        Returns
        -------
        dict
            Information about whether the job was queued.
        """

        # -------------------------------------------------
        # Validate diagnosis ID
        # -------------------------------------------------

        try:
            normalized_diagnosis_id = int(
                diagnosis_id
            )

        except (
            TypeError,
            ValueError,
        ) as error:

            return {
                "status": "not_queued",
                "queued": False,
                "diagnosis_id": None,
                "error": (
                    "Invalid diagnosis ID: "
                    f"{error}"
                ),
            }

        # -------------------------------------------------
        # Get current Flask application
        # -------------------------------------------------

        try:
            app = current_app._get_current_object()

        except RuntimeError as error:

            return {
                "status": "not_queued",
                "queued": False,
                "diagnosis_id": normalized_diagnosis_id,
                "error": (
                    "No active Flask application context: "
                    f"{error}"
                ),
            }

        # -------------------------------------------------
        # Create background thread
        # -------------------------------------------------

        try:

            thread = threading.Thread(
                target=self._run_outbreak_job,
                args=(
                    app,
                    normalized_diagnosis_id,
                ),
                name=(
                    f"outbreak-job-"
                    f"{normalized_diagnosis_id}"
                ),
                daemon=True,
            )

            thread.start()

            return {
                "status": "queued",
                "queued": True,
                "diagnosis_id": normalized_diagnosis_id,
            }

        except Exception as error:

            return {
                "status": "not_queued",
                "queued": False,
                "diagnosis_id": normalized_diagnosis_id,
                "error": str(error),
            }

    # =====================================================
    # SAVE DIAGNOSIS RECORD
    # =====================================================

    def _save_diagnosis_record(
        self,
        diagnosis_result: dict[str, Any],
        image_path: Path,
        explain: bool,
        user_id: int | None = None,
    ) -> DiagnosisRecord:
        """
        Save a successful ML diagnosis to PostgreSQL.

        Parameters
        ----------
        diagnosis_result:
            Structured result returned by the ML service.

        image_path:
            Actual uploaded image path.

        explain:
            Whether Grad-CAM explanation was requested.

        user_id:
            Authenticated user's database ID.
        """

        # =================================================
        # VALIDATE RESULT
        # =================================================

        if not isinstance(
            diagnosis_result,
            dict,
        ):
            raise DiagnosisIntegrationError(
                "Diagnosis result must be a dictionary."
            )

        # =================================================
        # PREDICTION
        # =================================================

        prediction = diagnosis_result.get(
            "prediction"
        )

        if not isinstance(
            prediction,
            dict,
        ):
            raise DiagnosisIntegrationError(
                "Diagnosis result does not contain "
                "a valid prediction."
            )

        # =================================================
        # DISEASE CLASS
        # =================================================

        disease_class = prediction.get(
            "class_name"
        )

        if not disease_class:
            disease_class = prediction.get(
                "display_name"
            )

        if not disease_class:
            raise DiagnosisIntegrationError(
                "Diagnosis result does not contain "
                "a disease class."
            )

        disease_class = str(
            disease_class
        ).strip()

        # =================================================
        # CONFIDENCE
        # =================================================

        confidence = prediction.get(
            "confidence"
        )

        if confidence is None:
            raise DiagnosisIntegrationError(
                "Diagnosis result does not contain "
                "a confidence value."
            )

        try:
            confidence = float(
                confidence
            )

        except (
            TypeError,
            ValueError,
        ) as error:

            raise DiagnosisIntegrationError(
                "Diagnosis confidence must be numeric."
            ) from error

        # =================================================
        # MODEL INFORMATION
        # =================================================

        model_name = prediction.get(
            "model"
        )

        model_version = prediction.get(
            "version"
        )

        prediction_time = prediction.get(
            "prediction_time"
        )

        # -------------------------------------------------
        # Validate prediction time if available
        # -------------------------------------------------

        if prediction_time is not None:

            try:
                prediction_time = float(
                    prediction_time
                )

            except (
                TypeError,
                ValueError,
            ) as error:

                raise DiagnosisIntegrationError(
                    "Prediction time must be numeric."
                ) from error

        # =================================================
        # EXPLAINABILITY
        # =================================================

        heatmap_path = None

        explainability = diagnosis_result.get(
            "explainability"
        )

        # -------------------------------------------------
        # Standard ML response format
        # -------------------------------------------------

        if isinstance(
            explainability,
            dict,
        ):

            heatmap_path = (
                explainability.get("overlay")
                or explainability.get("heatmap")
            )

        # -------------------------------------------------
        # Also support flat response format
        # -------------------------------------------------

        if heatmap_path is None:

            heatmap_path = diagnosis_result.get(
                "heatmap_path"
            )

        # Explainability flag
        explainability_requested = bool(
            explain
        )

        # =================================================
        # IMAGE INFORMATION
        # =================================================

        normalized_image_path = Path(
            image_path
        )

        image_filename = (
            normalized_image_path.name
        )

        image_path_string = str(
            normalized_image_path
        )

        # =================================================
        # USER ID
        # =================================================

        normalized_user_id: int | None = None

        if user_id is not None:

            try:
                normalized_user_id = int(
                    user_id
                )

            except (
                TypeError,
                ValueError,
            ) as error:

                raise DiagnosisIntegrationError(
                    "User ID must be an integer."
                ) from error

        # =================================================
        # CREATE RECORD
        # =================================================

        record = DiagnosisRecord(
            user_id=normalized_user_id,

            image_filename=image_filename,

            image_path=image_path_string,

            disease_class=disease_class,

            confidence=confidence,

            model_name=(
                str(model_name)
                if model_name is not None
                else None
            ),

            model_version=(
                str(model_version)
                if model_version is not None
                else None
            ),

            prediction_time=prediction_time,

            explainability_requested=(
                explainability_requested
            ),

            heatmap_path=(
                str(heatmap_path)
                if heatmap_path
                else None
            ),
        )

                # =================================================
        # DATABASE COMMIT WITH RETRY
        # =================================================

        def save_diagnosis_record():
            """
            Save the diagnosis record as one database
            transaction operation.

            DatabaseRetryService handles transient
            database connection/timeout failures.
            """

            db.session.add(
                record
            )

            db.session.commit()

            return record

        try:

            database_result = (
                DatabaseRetryService.execute(
                    operation=save_diagnosis_record,
                    max_attempts=3,
                )
            )

        except Exception as error:

            raise DiagnosisIntegrationError(
                "Failed to save diagnosis record."
            ) from error

        record = database_result["result"]
        return record
    # =====================================================
    # MAIN DIAGNOSIS
    # =====================================================

    def diagnose(
        self,
        image_path: str | Path,
        explain: bool = False,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Run AI diagnosis, save the result, queue outbreak
        processing asynchronously, and return immediately.

        IMPORTANT
        ---------
        The outbreak job is NOT awaited.

        Therefore:

            AI diagnosis
                |
                v
            Database save
                |
                v
            Return response
                |
                +---- background outbreak job

        This prevents outbreak analysis and SMS processing
        from slowing down the farmer's diagnosis response.
        """

        # =================================================
        # CHECK ML SERVICE
        # =================================================

        if not self.is_ready():

            raise DiagnosisIntegrationError(
                "Diagnosis service is not ready."
            )

        # =================================================
        # VALIDATE IMAGE PATH
        # =================================================

        if not image_path:

            raise DiagnosisIntegrationError(
                "Image path is required."
            )

        path = Path(
            image_path
        )

        if not path.exists():

            raise DiagnosisIntegrationError(
                f"Image file not found: {path}"
            )

        if not path.is_file():

            raise DiagnosisIntegrationError(
                f"Image path is not a file: {path}"
            )

        # =================================================
        # RUN AI DIAGNOSIS
        # =================================================

        try:

            result = (
                self._diagnosis_service.diagnose(
                    image_path=str(path),
                    explain=bool(explain),
                )
            )

        except Exception as error:

            raise DiagnosisIntegrationError(
                f"AI diagnosis failed: {error}"
            ) from error

        # =================================================
        # VALIDATE AI RESULT
        # =================================================

        if result is None:

            raise DiagnosisIntegrationError(
                "AI diagnosis returned no result."
            )

        # -------------------------------------------------
        # Support dictionary result
        # -------------------------------------------------

        if isinstance(
            result,
            dict,
        ):

            diagnosis_result = result

        # -------------------------------------------------
        # Support result objects with to_dict()
        # -------------------------------------------------

        elif hasattr(
            result,
            "to_dict",
        ):

            try:

                diagnosis_result = (
                    result.to_dict()
                )

            except Exception as error:

                raise DiagnosisIntegrationError(
                    "Unable to serialize AI diagnosis result."
                ) from error

        else:

            raise DiagnosisIntegrationError(
                "AI diagnosis returned an unsupported "
                "result type: "
                f"{type(result).__name__}"
            )

        # =================================================
        # VALIDATE PREDICTION
        # =================================================

        prediction = diagnosis_result.get(
            "prediction"
        )

        if not isinstance(
            prediction,
            dict,
        ):

            raise DiagnosisIntegrationError(
                "AI diagnosis returned no valid prediction."
            )

        # =================================================
        # SAVE DIAGNOSIS
        # =================================================

        record = self._save_diagnosis_record(
            diagnosis_result=diagnosis_result,
            image_path=path,
            explain=bool(explain),
            user_id=user_id,
        )

        # =================================================
        # DATABASE ID
        # =================================================

        diagnosis_result["database_id"] = (
            record.id
        )

        # =================================================
        # QUEUE OUTBREAK PROCESSING
        # =================================================
        #
        # IMPORTANT:
        #
        # The database record has already been committed.
        #
        # The background job can therefore safely query
        # diagnosis_records and see this diagnosis.
        #
        # We DO NOT wait for the result.
        # =================================================

        outbreak_job = (
            self._queue_outbreak_job(
                record.id
            )
        )

        # =================================================
        # RESPONSE OUTBREAK STATUS
        # =================================================

        diagnosis_result["outbreak"] = {
            "status": outbreak_job.get(
                "status",
                "unknown",
            ),

            "queued": outbreak_job.get(
                "queued",
                False,
            ),

            "diagnosis_id": record.id,
        }

        # =================================================
        # RETURN IMMEDIATELY
        # =================================================

        return diagnosis_result

    # =====================================================
    # PROPERTIES
    # =====================================================

    @property
    def diagnosis_service(self) -> Any:
        """
        Return the underlying ML DiagnosisService.

        Useful for testing and advanced service-level
        integration.
        """

        return self._diagnosis_service
