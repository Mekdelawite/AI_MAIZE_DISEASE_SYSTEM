"""Leader-elected daily scheduler for automatic crop notifications.

Every Flask worker may start a lightweight contender. A PostgreSQL session
advisory lock elects exactly one worker for the scheduler lifetime; losing the
connection releases leadership so another worker can take over.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.app.extensions import db
from backend.app.models import FarmerProfile, SMSRecord, User
from backend.app.services.crop_calendar_notification_service import CropCalendarNotificationService
from backend.app.services.sms_service import SMSService

_SCHEDULER_LOCK_ID = 824_510_275
_started_apps: set[int] = set()
_guard = threading.Lock()


def deliver_deferred_urgent_sms() -> int:
    """Deliver opted-in urgent SMS records once quiet hours permit it."""
    delivered = 0
    pending = SMSRecord.query.filter_by(status="deferred").order_by(SMSRecord.id.asc()).all()
    for record in pending:
        try:
            user = db.session.get(User, record.user_id) if record.user_id is not None else None
            profile = db.session.get(FarmerProfile, record.user_id) if record.user_id is not None else None
            if user is None or profile is None or not profile.sms_opt_in or not user.phone_number:
                record.status = "cancelled"
                db.session.commit()
                continue
            preferences = CropCalendarNotificationService.preferences(profile)
            if not preferences["categories"]["important_alerts"]["sms"]:
                record.status = "cancelled"
                db.session.commit()
                continue
            if CropCalendarNotificationService.quiet_now(profile, critical=True):
                continue
            SMSService.send_sms(
                record.recipient_phone, record.message, recipient_type="farmer",
                notification_type=record.notification_type, language=record.language,
                user_id=user.id, region=record.region, woreda=record.woreda, kebele=record.kebele,
                outbreak_alert_id=record.outbreak_alert_id, dedupe_key=record.dedupe_key,
            )
            delivered += 1
        except Exception:
            db.session.rollback()
            from flask import current_app
            current_app.logger.exception("Deferred urgent SMS delivery failed (record_id=%s).", record.id)
    return delivered


def start_smart_notification_scheduler(app) -> None:
    if not app.config.get("SMART_NOTIFICATIONS_ENABLED", True) or app.config.get("TESTING"):
        return
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    with _guard:
        if id(app) in _started_apps:
            return
        _started_apps.add(id(app))

    def scheduler_loop() -> None:
        while True:
            connection = None
            try:
                with app.app_context():
                    if db.engine.dialect.name != "postgresql":
                        app.logger.error("Smart notification scheduler requires PostgreSQL advisory locks; scheduler is disabled.")
                        return
                    connection = db.engine.connect()
                    acquired = bool(connection.exec_driver_sql(
                        "SELECT pg_try_advisory_lock(%s)", (_SCHEDULER_LOCK_ID,)
                    ).scalar())
                    connection.commit()
                    if not acquired:
                        connection.close()
                        connection = None
                        time.sleep(30)
                        continue
                    app.logger.info("This worker is the smart notification scheduler leader.")
                    last_weather_day = None
                    while True:
                        try:
                            with app.app_context():
                                current_day = datetime.now(ZoneInfo("Africa/Addis_Ababa")).date()
                                include_weather = current_day != last_weather_day
                                CropCalendarNotificationService.run_daily(include_weather=include_weather)
                                deliver_deferred_urgent_sms()
                                if include_weather:
                                    last_weather_day = current_day
                        except Exception:
                            app.logger.exception("Scheduled smart notification run failed.")
                        try:
                            connection.exec_driver_sql("SELECT 1").scalar()
                            connection.commit()
                        except Exception:
                            app.logger.exception("Smart notification scheduler lost its leadership connection.")
                            break
                        # Poll reminders so quiet-hour delays are delivered as soon as
                        # the farmer's local quiet period ends. Weather remains daily.
                        time.sleep(15 * 60)
            except Exception:
                app.logger.exception("Smart notification scheduler could not acquire leadership.")
                time.sleep(60)
            finally:
                if connection is not None:
                    try:
                        connection.exec_driver_sql(
                            "SELECT pg_advisory_unlock(%s)", (_SCHEDULER_LOCK_ID,)
                        )
                    except Exception:
                        pass
                    connection.close()

    thread = threading.Thread(target=scheduler_loop, name="maizecare-smart-notifications", daemon=True)
    thread.start()
