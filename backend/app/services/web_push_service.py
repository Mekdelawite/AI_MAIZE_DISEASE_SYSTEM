"""Web Push delivery for existing farmer notification records."""
from __future__ import annotations

import json
import base64
import re
from datetime import datetime, timedelta, timezone

from flask import current_app, has_app_context
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models import (
    FarmerNotification,
    FarmerProfile,
    FarmerPushDelivery,
    FarmerPushSubscription,
    User,
)

MAX_ATTEMPTS = 5
MAX_DELIVERIES_PER_POLL = 100
CRITICAL_NOTIFICATION_TYPES = {"outbreak_alert", "regional_alert"}
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")


class WebPushService:
    @staticmethod
    def is_configured() -> bool:
        if not has_app_context():
            return False
        public_key = current_app.config.get("WEB_PUSH_VAPID_PUBLIC_KEY", "")
        private_key = current_app.config.get("WEB_PUSH_VAPID_PRIVATE_KEY", "")
        subject = current_app.config.get("WEB_PUSH_VAPID_SUBJECT", "")
        valid_public_key = isinstance(public_key, str) and bool(_BASE64URL.fullmatch(public_key))
        if valid_public_key:
            try:
                decoded_key = base64.urlsafe_b64decode(
                    public_key + "=" * (-len(public_key) % 4)
                )
                valid_public_key = len(decoded_key) == 65 and decoded_key[0] == 4
            except (ValueError, base64.binascii.Error):
                valid_public_key = False
        return bool(
            public_key
            and valid_public_key
            and private_key
            and (
                subject.startswith("mailto:")
                or subject.startswith("https://")
            )
        )

    @staticmethod
    def _category(notification_type: str) -> str:
        from backend.app.services.crop_calendar_notification_service import (
            CropCalendarNotificationService,
        )

        return CropCalendarNotificationService.CATEGORY_MAP.get(
            notification_type,
            "important_alerts",
        )

    @classmethod
    def enqueue_notification(cls, notification: FarmerNotification) -> int:
        """Create at most one delivery receipt per existing notification/device."""
        if not cls.is_configured():
            return 0

        profile = db.session.get(FarmerProfile, notification.user_id)
        if profile is None:
            return 0
        category = cls._category(notification.notification_type)
        preferences = cls._preferences(profile)
        if not preferences["categories"][category]["push"]:
            return 0

        subscriptions = FarmerPushSubscription.query.filter_by(
            user_id=notification.user_id,
        ).all()
        queued = 0
        for subscription in subscriptions:
            if FarmerPushDelivery.query.filter_by(
                notification_id=notification.id,
                subscription_id=subscription.id,
            ).first():
                continue
            try:
                with db.session.begin_nested():
                    db.session.add(FarmerPushDelivery(
                        notification_id=notification.id,
                        subscription_id=subscription.id,
                    ))
                    db.session.flush()
                queued += 1
            except IntegrityError:
                # Another worker already queued this notification for the device.
                continue

        if queued:
            db.session.commit()
            cls.deliver_notification(notification.id)
        return queued

    @staticmethod
    def _preferences(profile) -> dict:
        from backend.app.services.crop_calendar_notification_service import (
            CropCalendarNotificationService,
        )

        return CropCalendarNotificationService.preferences(profile)

    @classmethod
    def _deliver(cls, delivery_id: int) -> bool:
        now = datetime.now(timezone.utc)
        claimed = db.session.execute(
            update(FarmerPushDelivery)
            .where(
                FarmerPushDelivery.id == delivery_id,
                FarmerPushDelivery.status == "pending",
                FarmerPushDelivery.next_attempt_at <= now,
            )
            .values(
                status="sending",
                attempts=FarmerPushDelivery.attempts + 1,
            )
        )
        db.session.commit()
        if claimed.rowcount != 1:
            return False

        delivery = db.session.get(FarmerPushDelivery, delivery_id)
        notification = db.session.get(
            FarmerNotification,
            delivery.notification_id,
        ) if delivery else None
        subscription = db.session.get(
            FarmerPushSubscription,
            delivery.subscription_id,
        ) if delivery else None
        if delivery is None or notification is None or subscription is None:
            if delivery is not None:
                delivery.status = "cancelled"
                db.session.commit()
            return False

        user = db.session.get(User, notification.user_id)
        profile = db.session.get(FarmerProfile, notification.user_id)
        if user is None or not user.is_active or profile is None:
            delivery.status = "cancelled"
            db.session.commit()
            return False

        category = cls._category(notification.notification_type)
        preferences = cls._preferences(profile)
        if not preferences["categories"][category]["push"]:
            delivery.status = "cancelled"
            db.session.commit()
            return False

        critical = notification.notification_type in CRITICAL_NOTIFICATION_TYPES
        from backend.app.services.crop_calendar_notification_service import (
            CropCalendarNotificationService,
        )

        if CropCalendarNotificationService.quiet_now(profile, critical=critical):
            delivery.status = "pending"
            delivery.next_attempt_at = now + timedelta(minutes=15)
            db.session.commit()
            return False

        language = "am" if str(user.preferred_language or "").lower().startswith("am") else "en"
        payload = {
            "title": "MaizeCare AI",
            "body": (
                "አዲስ የእርሻ መረጃ አለ። ዝርዝሩን ለማየት MaizeCare AIን ይክፈቱ።"
                if language == "am"
                else "A new farm update is ready. Open MaizeCare AI to view it."
            ),
            "url": "/farmer/dashboard",
        }

        from pywebpush import WebPushException, webpush
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=current_app.config["WEB_PUSH_VAPID_PRIVATE_KEY"],
                vapid_claims={
                    "sub": current_app.config["WEB_PUSH_VAPID_SUBJECT"],
                },
                ttl=3600,
                timeout=10,
            )
        except WebPushException as error:
            status_code = getattr(error, "status_code", None)
            if status_code is None:
                status_code = getattr(
                    getattr(error, "response", None),
                    "status_code",
                    None,
                )
            if status_code in (404, 410):
                db.session.delete(subscription)
                delivery.status = "expired"
                delivery.last_error = f"HTTP_{status_code}"
                db.session.commit()
                return False

            delivery.last_error = (
                f"HTTP_{status_code}" if status_code else type(error).__name__[:80]
            )
            if delivery.attempts < MAX_ATTEMPTS and (
                status_code is None or status_code == 429 or status_code >= 500
            ):
                delay_seconds = min(3600, 60 * (2 ** (delivery.attempts - 1)))
                delivery.status = "pending"
                delivery.next_attempt_at = now + timedelta(seconds=delay_seconds)
            else:
                delivery.status = "failed"
            db.session.commit()
            current_app.logger.warning(
                "Web Push delivery failed (delivery_id=%s, status=%s).",
                delivery.id,
                delivery.last_error,
            )
            return False
        except Exception as error:
            delivery.last_error = type(error).__name__[:80]
            if delivery.attempts < MAX_ATTEMPTS:
                delay_seconds = min(3600, 60 * (2 ** (delivery.attempts - 1)))
                delivery.status = "pending"
                delivery.next_attempt_at = now + timedelta(seconds=delay_seconds)
            else:
                delivery.status = "failed"
            db.session.commit()
            current_app.logger.warning(
                "Web Push delivery failed (delivery_id=%s, error=%s).",
                delivery.id,
                delivery.last_error,
            )
            return False

        delivery.status = "sent"
        delivery.sent_at = datetime.now(timezone.utc)
        delivery.last_error = None
        db.session.commit()
        return True

    @classmethod
    def deliver_notification(cls, notification_id: int) -> int:
        delivery_ids = [
            row.id
            for row in FarmerPushDelivery.query.filter_by(
                notification_id=notification_id,
                status="pending",
            ).all()
        ]
        return sum(cls._deliver(delivery_id) for delivery_id in delivery_ids)

    @classmethod
    def deliver_pending(cls, limit: int = MAX_DELIVERIES_PER_POLL) -> int:
        """Retry due push deliveries from the existing scheduler."""
        if not cls.is_configured():
            return 0
        due_ids = [
            row.id
            for row in FarmerPushDelivery.query.filter(
                FarmerPushDelivery.status == "pending",
                FarmerPushDelivery.next_attempt_at <= datetime.now(timezone.utc),
            )
            .order_by(FarmerPushDelivery.id.asc())
            .limit(limit)
            .all()
        ]
        return sum(cls._deliver(delivery_id) for delivery_id in due_ids)
