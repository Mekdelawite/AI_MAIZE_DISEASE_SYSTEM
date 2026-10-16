"""
=========================================================
SMS Retry Service
=========================================================

Controlled retry handling for failed SMS records.

Responsibilities:
    - Retry failed SMS records only
    - Preserve the original SMSRecord
    - Reuse SMSService.send_sms()
    - Create a new SMSRecord for every retry submission
    - Limit retries to a maximum of 3 per operation

Important:
    Automatic retry is intentionally NOT performed inside
    SMSService.send_sms() because a provider timeout can
    happen after the provider has accepted an SMS, which
    could otherwise create duplicate messages.

=========================================================
"""

from __future__ import annotations

from typing import Any

from backend.app.extensions import db
from backend.app.models.sms_record import SMSRecord
from backend.app.services.sms_service import SMSService


class SMSRetryService:
    """
    Controlled retry service for failed SMS records.

    The original SMSRecord is preserved as an audit record.

    Every retry is submitted through SMSService.send_sms(),
    which creates a new SMSRecord for that submission.

    No automatic retry is performed by this service.
    """

    MAX_RETRIES = 3

    @classmethod
    def retry_sms(
        cls,
        sms_record_id: int,
        *,
        max_retries: int = MAX_RETRIES,
    ) -> dict[str, Any]:
        """
        Retry a failed SMS record.

        Only records with status='failed' can be retried.

        The original SMSRecord is never modified or deleted.

        Parameters
        ----------
        sms_record_id:
            ID of the original failed SMSRecord.

        max_retries:
            Maximum number of retry submissions for this
            operation. The value is capped at MAX_RETRIES.

        Returns
        -------
        dict[str, Any]
            Retry result information.
        """

        # =====================================================
        # VALIDATE SMS RECORD ID
        # =====================================================

        try:
            sms_record_id = int(
                sms_record_id
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                "SMS record ID must be a valid integer."
            ) from exc

        # =====================================================
        # VALIDATE RETRY LIMIT
        # =====================================================

        try:
            max_retries = int(
                max_retries
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                "max_retries must be a valid integer."
            ) from exc

        if max_retries < 1:

            raise ValueError(
                "max_retries must be at least 1."
            )

        max_retries = min(
            max_retries,
            cls.MAX_RETRIES,
        )

        # =====================================================
        # LOAD ORIGINAL SMS RECORD
        # =====================================================

        original = db.session.get(
            SMSRecord,
            sms_record_id,
        )

        if original is None:

            raise ValueError(
                f"SMS record {sms_record_id} was not found."
            )

        # =====================================================
        # ONLY FAILED SMS CAN BE RETRIED
        # =====================================================

        if original.status != "failed":

            raise ValueError(
                "Only failed SMS records can be retried."
            )

        # =====================================================
        # PERFORM CONTROLLED RETRIES
        # =====================================================

        results: list[
            dict[str, Any]
        ] = []

        for attempt in range(
            1,
            max_retries + 1,
        ):

            try:

                # Reuse the existing SMS communication
                # logic. Do NOT duplicate provider handling.
                result = SMSService.send_sms(
                    recipient_phone=(
                        original.recipient_phone
                    ),
                    message=(
                        original.message
                    ),
                    recipient_type=(
                        original.recipient_type
                    ),
                    notification_type=(
                        original.notification_type
                    ),
                    language=(
                        original.language
                    ),
                    user_id=(
                        original.user_id
                    ),
                    region=(
                        original.region
                    ),
                    woreda=(
                        original.woreda
                    ),
                    kebele=(
                        original.kebele
                    ),
                    outbreak_alert_id=(
                        original.outbreak_alert_id
                    ),
                )

            except Exception as exc:

                result = {
                    "success": False,
                    "status": "failed",
                    "error": str(exc),
                }

            # -------------------------------------------------
            # STORE THIS RETRY RESULT
            # -------------------------------------------------

            results.append(
                {
                    "attempt": attempt,
                    "result": result,
                }
            )

            # -------------------------------------------------
            # STOP AFTER SUCCESS
            # -------------------------------------------------

            if result.get(
                "success"
            ):

                return {
                    "success": True,
                    "status": result.get(
                        "status"
                    ),
                    "original_sms_record_id": (
                        original.id
                    ),
                    "retry_attempts": attempt,
                    "retry_sms_record_id": (
                        result.get(
                            "sms_record_id"
                        )
                    ),
                    "result": result,
                }

        # =====================================================
        # ALL RETRIES FAILED
        # =====================================================

        last_result = (
            results[-1]["result"]
            if results
            else {}
        )

        return {
            "success": False,
            "status": "failed",
            "original_sms_record_id": (
                original.id
            ),
            "retry_attempts": max_retries,
            "last_result": last_result,
            "attempts": results,
        }