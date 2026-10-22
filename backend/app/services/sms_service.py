
"""
=========================================================
SMS Service
=========================================================

Handles SMS communication for the AI Maize Disease
Detection System using Africa's Talking HTTP API.

Responsibilities:
    - Validate SMS configuration
    - Normalize recipient phone numbers
    - Send SMS messages
    - Record SMS attempts in PostgreSQL
    - Track provider responses and failures
    - Support farmer and extension-agent notifications
    - Support English and Amharic notifications
    - Link outbreak SMS records to OutbreakAlert
=========================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from flask import current_app

from backend.app.extensions import db
from backend.app.models.sms_record import SMSRecord


class SMSService:
    """Send and track Africa's Talking SMS notifications."""

    # =====================================================
    # CONFIGURATION
    # =====================================================

    @staticmethod
    def _get_api_url() -> str:
        """Return the Africa's Talking SMS endpoint."""

        environment = str(
            current_app.config.get(
                "AFRICASTALKING_ENVIRONMENT",
                "sandbox",
            )
        ).lower()

        if environment == "sandbox":
            return (
                "https://api.sandbox.africastalking.com"
                "/version1/messaging"
            )

        return (
            "https://api.africastalking.com"
            "/version1/messaging"
        )

    @staticmethod
    def _validate_configuration() -> tuple[str, str]:
        """Validate and return the configured username and API key."""

        username = current_app.config.get(
            "AFRICASTALKING_USERNAME",
            "",
        )
        api_key = current_app.config.get(
            "AFRICASTALKING_API_KEY",
            "",
        )

        if not username:
            raise RuntimeError(
                "AFRICASTALKING_USERNAME is not configured."
            )

        if not api_key:
            raise RuntimeError(
                "AFRICASTALKING_API_KEY is not configured."
            )

        return str(username), str(api_key)

    # =====================================================
    # PHONE NUMBER NORMALIZATION
    # =====================================================

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """
        Normalize Ethiopian phone numbers.

        Examples:
            0911998877    -> +251911998877
            251911998877  -> +251911998877
            +251911998877 -> +251911998877
        """

        phone = str(phone).strip()

        phone = (
            phone
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )

        if phone.startswith("09") and len(phone) == 10:
            phone = "+251" + phone[1:]

        elif phone.startswith("251") and len(phone) == 12:
            phone = "+" + phone

        elif phone.startswith("+251") and len(phone) == 13:
            pass

        return phone

    # =====================================================
    # PARSE AFRICA'S TALKING RESPONSE
    # =====================================================

    @staticmethod
    def _parse_provider_response(
        response_body: str,
    ) -> dict[str, Any]:
        """Parse Africa's Talking XML response."""

        if not response_body:
            return {}

        try:
            root = ElementTree.fromstring(response_body)
        except ElementTree.ParseError:
            return {"raw_body": response_body}

        message_element = root.find(
            ".//SMSMessageData/Message"
        )

        recipient_element = root.find(
            ".//SMSMessageData/Recipients/Recipient"
        )

        result: dict[str, Any] = {
            "message": (
                message_element.text
                if message_element is not None
                else None
            ),
            "recipients": [],
        }

        if recipient_element is not None:
            recipient = {
                "number": recipient_element.findtext("number"),
                "cost": recipient_element.findtext("cost"),
                "status": recipient_element.findtext("status"),
                "statusCode": recipient_element.findtext(
                    "statusCode"
                ),
                "messageId": recipient_element.findtext(
                    "messageId"
                ),
            }

            result["recipients"].append(recipient)

        return result

    # =====================================================
    # SEND SMS
    # =====================================================

    @classmethod
    def send_sms(
        cls,
        recipient_phone: str,
        message: str,
        *,
        recipient_type: str = "farmer",
        notification_type: str = "general",
        language: str = "en",
        user_id: int | None = None,
        region: str | None = None,
        woreda: str | None = None,
        kebele: str | None = None,
        outbreak_alert_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Send an SMS and record the result in PostgreSQL.

        The transport uses Python's standard HTTPS client.
        TLS certificate verification remains enabled.
        """

        phone = cls._normalize_phone(recipient_phone)

        if not message or not message.strip():
            raise ValueError("SMS message cannot be empty.")

        # -------------------------------------------------
        # Create database record
        # -------------------------------------------------

        sms_record = SMSRecord(
            recipient_phone=phone,
            recipient_type=recipient_type,
            message=message,
            language=language,
            notification_type=notification_type,
            provider="africas_talking",
            status="pending",
            user_id=user_id,
            outbreak_alert_id=outbreak_alert_id,
            region=region,
            woreda=woreda,
            kebele=kebele,
        )

        db.session.add(sms_record)
        db.session.commit()

        # -------------------------------------------------
        # Send SMS
        # -------------------------------------------------

        try:
            username, api_key = cls._validate_configuration()
            api_url = cls._get_api_url()

            sender_id = current_app.config.get(
                "AFRICASTALKING_SENDER_ID",
                "",
            )

            fields = {
                "username": username,
                "to": phone,
                "message": message,
            }

            if sender_id:
                fields["from"] = str(sender_id)

            request_data = urlencode(fields).encode("utf-8")

            request = Request(
                api_url,
                data=request_data,
                headers={
                    "apiKey": api_key,
                    "Accept": "application/xml",
                    "Content-Type": (
                        "application/x-www-form-urlencoded"
                    ),
                },
                method="POST",
            )

            # HTTPError is handled separately because urllib
            # raises it for HTTP 4xx and 5xx responses.
            try:
                with urlopen(request, timeout=30.0) as response:
                    response_status = response.status
                    response_body = response.read().decode(
                        "utf-8",
                        "replace",
                    )
            except HTTPError as exc:
                response_status = exc.code
                response_body = exc.read().decode(
                    "utf-8",
                    "replace",
                )

            # -------------------------------------------------
            # Check HTTP response
            # -------------------------------------------------

            if not 200 <= response_status < 300:
                parsed_error = cls._parse_provider_response(
                    response_body
                )

                error_message = (
                    parsed_error.get("message")
                    or response_body
                    or (
                        "Africa's Talking returned "
                        f"HTTP {response_status}."
                    )
                )

                sms_record.status = "failed"
                sms_record.error_message = str(error_message)
                sms_record.updated_at = datetime.now(
                    timezone.utc
                )

                db.session.commit()

                return {
                    "success": False,
                    "status": "failed",
                    "provider": "africas_talking",
                    "phone": phone,
                    "error": str(error_message),
                    "http_status": response_status,
                    "sms_record_id": sms_record.id,
                    "outbreak_alert_id": outbreak_alert_id,
                }

            # -------------------------------------------------
            # Process provider response
            # -------------------------------------------------

            parsed_response = cls._parse_provider_response(
                response_body
            )

            recipients_data = parsed_response.get(
                "recipients",
                [],
            )

            recipient_data = (
                recipients_data[0]
                if recipients_data
                else {}
            )

            status_code = str(
                recipient_data.get("statusCode") or ""
            )

            provider_message_id = recipient_data.get(
                "messageId"
            )

            provider_status = recipient_data.get("status")

            status = cls._map_provider_status(status_code)

            # -------------------------------------------------
            # Update database record
            # -------------------------------------------------

            sms_record.provider_message_id = provider_message_id
            sms_record.status = status

            if status in {"sent", "submitted"}:
                sms_record.sent_at = datetime.now(timezone.utc)

            sms_record.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            # -------------------------------------------------
            # Return result
            # -------------------------------------------------

            return {
                "success": status in {"sent", "submitted"},
                "status": status,
                "provider": "africas_talking",
                "provider_status": provider_status,
                "provider_status_code": status_code,
                "provider_message_id": provider_message_id,
                "phone": phone,
                "message": message,
                "http_status": response_status,
                "raw_response": parsed_response,
                "sms_record_id": sms_record.id,
                "outbreak_alert_id": outbreak_alert_id,
            }

        except Exception as exc:
            # -------------------------------------------------
            # Record failure
            # -------------------------------------------------

            db.session.rollback()

            try:
                sms_record.status = "failed"
                sms_record.error_message = str(exc)
                sms_record.updated_at = datetime.now(
                    timezone.utc
                )

                db.session.commit()

            except Exception:
                db.session.rollback()
                current_app.logger.exception(
                    "Could not save the SMS failure record."
                )

            current_app.logger.exception(
                "Africa's Talking SMS request failed."
            )

            return {
                "success": False,
                "status": "failed",
                "provider": "africas_talking",
                "phone": phone,
                "error": str(exc),
                "sms_record_id": sms_record.id,
                "outbreak_alert_id": outbreak_alert_id,
            }

    # =====================================================
    # STATUS MAPPING
    # =====================================================

    @staticmethod
    def _map_provider_status(status_code: str) -> str:
        """Map provider status codes to application statuses."""

        if status_code == "101":
            return "sent"

        if status_code in {"102", "103"}:
            return "submitted"

        if status_code in {
            "400", "401", "402", "403", "404",
            "405", "406", "407", "408", "409",
            "410", "500",
        }:
            return "failed"

        return "pending"

    # =====================================================
    # DISEASE ALERT
    # =====================================================

    @classmethod
    def send_disease_alert(
        cls,
        recipient_phone: str,
        disease_name: str,
        confidence: float,
        *,
        language: str = "en",
        user_id: int | None = None,
        region: str | None = None,
        woreda: str | None = None,
        kebele: str | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        """Send a disease diagnosis alert."""

        if message and message.strip():
            alert_message = message.strip()
        elif language == "am":
            alert_message = (
                f"የበቆሎ በሽታ ተገኝቷል፦ {disease_name} "
                f"({confidence:.2f}%). "
                "እባክዎ ተገቢውን የህክምና ምክር ይከተሉ።"
            )
        else:
            alert_message = (
                f"Maize disease detected: {disease_name} "
                f"({confidence:.2f}%). Please follow the "
                "recommended treatment advice."
            )

        return cls.send_sms(
            recipient_phone,
            alert_message,
            recipient_type="farmer",
            notification_type="disease_alert",
            language=language,
            user_id=user_id,
            region=region,
            woreda=woreda,
            kebele=kebele,
        )

    # =====================================================
    # OUTBREAK ALERT
    # =====================================================

    @classmethod
    def send_outbreak_alert(
        cls,
        recipient_phone: str,
        disease_name: str,
        location: str,
        *,
        language: str = "en",
        user_id: int | None = None,
        region: str | None = None,
        woreda: str | None = None,
        kebele: str | None = None,
        outbreak_alert_id: int | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        """Send a disease outbreak alert."""

        if message and message.strip():
            alert_message = message.strip()
        elif language == "am":
            alert_message = (
                "የበቆሎ በሽታ ስርጭት ማስጠንቀቂያ፦ "
                f"{disease_name} በ{location} ተመዝግቧል። "
                "እባክዎ ሰብልዎን ይከታተሉ እና "
                "ተገቢውን ምክር ይከተሉ።"
            )
        else:
            alert_message = (
                f"Maize disease outbreak alert: {disease_name} "
                f"has been reported in {location}. "
                "Please monitor your crops and follow the "
                "recommended advice."
            )

        return cls.send_sms(
            recipient_phone,
            alert_message,
            recipient_type="farmer",
            notification_type="outbreak_alert",
            language=language,
            user_id=user_id,
            outbreak_alert_id=outbreak_alert_id,
            region=region,
            woreda=woreda,
            kebele=kebele,
        )
