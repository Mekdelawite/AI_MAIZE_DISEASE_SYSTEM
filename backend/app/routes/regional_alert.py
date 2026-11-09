"""Admin broadcast alerts to farmers by region."""
from datetime import datetime, timedelta, timezone
import hashlib

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from backend.app.extensions import db
from backend.app.models import DiscussionPost, FarmerNotification, FarmerProfile, SMSRecord, User
from backend.app.services.sms_service import SMSService
from backend.app.services.crop_calendar_notification_service import CropCalendarNotificationService

regional_alert_bp = Blueprint("regional_alert", __name__, url_prefix="/api")

REGIONS = {
    "oromia", "amhara", "snnpr", "sidama", "south west ethiopia", "tigray",
    "benishangul-gumuz", "gambela", "somali", "afar", "harari", "dire dawa", "addis ababa",
}


def _farmer_access():
    if str(get_jwt().get("role", "")).lower() != "farmer":
        return None, (jsonify({"success": False, "message": "Farmer access required."}), 403)
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None, (jsonify({"success": False, "message": "Authenticated user identity is invalid."}), 401)
    user = db.session.get(User, user_id)
    if user is None or user.role != "farmer" or not user.is_active:
        return None, (jsonify({"success": False, "message": "Active farmer account not found."}), 403)
    return user_id, None


def _region_key(value):
    return " ".join(str(value or "").casefold().split())


@regional_alert_bp.post("/admin/regional-alerts")
@jwt_required()
def send_regional_alert():
    if str(get_jwt().get("role", "")).lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Request body must be a JSON object."}), 400
    raw_regions = data.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions or any(not isinstance(region, str) for region in raw_regions):
        return jsonify({"success": False, "message": "Select one or more valid Ethiopian regions."}), 400
    regions = list(dict.fromkeys(region.strip() for region in raw_regions if region.strip()))
    message_en = str(data.get("message_en", "")).strip()
    message_am = str(data.get("message_am", "")).strip()
    method = str(data.get("method", "")).lower()
    if not regions or any(_region_key(region) not in REGIONS for region in regions):
        return jsonify({"success": False, "message": "Select one or more valid Ethiopian regions."}), 400
    if not message_en or not message_am or len(message_en) > 5000 or len(message_am) > 5000:
        return jsonify({"success": False, "message": "Enter both messages (up to 5,000 characters each)."}), 400
    if method not in {"sms", "app", "both"}:
        return jsonify({"success": False, "message": "Delivery method must be sms, app, or both."}), 400

    try:
        recipient_rows = (db.session.query(User, FarmerProfile)
            .join(FarmerProfile, FarmerProfile.user_id == User.id)
            .filter(User.role == "farmer", User.is_active.is_(True))
            .all())
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not load farmers for regional alert.")
        return jsonify({"success": False, "message": "Could not load regional alert recipients."}), 500
    recipients_by_region = {region: [(user, profile) for user, profile in recipient_rows
        if _region_key(profile.region) == _region_key(region)] for region in regions}
    recipients = [(region, user, profile) for region, pairs in recipients_by_region.items()
        for user, profile in pairs]
    if not recipients:
        return jsonify({"success": True, "code": "NO_FARMERS", "message": "No farmers registered in this region.", "farmer_count": 0}), 200

    try:
        admin_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Authenticated administrator identity is invalid."}), 401
    posts = {}
    app_notifications_created = 0
    app_notification_error = None
    app_notifications = []
    sms_accepted = sms_pending = sms_failed = sms_duplicates_skipped = 0
    sms_results = []
    duplicate_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    try:
        if method in {"app", "both"}:
            try:
                for region, pairs in recipients_by_region.items():
                    if not pairs:
                        continue
                    post_content = f"English:\n{message_en}\n\nአማርኛ:\n{message_am}"
                    post = DiscussionPost.query.filter_by(
                        author_id=admin_id, post_type="alert", target_region=region,
                        title=f"Regional alert: {region}", content=post_content,
                    ).filter(DiscussionPost.created_at >= duplicate_cutoff).first()
                    if post is None:
                        post = DiscussionPost(author_id=admin_id, post_type="alert",
                            title=f"Regional alert: {region}", content=post_content,
                            target_region=region, priority="urgent")
                        db.session.add(post)
                        db.session.flush()
                    posts[region] = post
                for region, user, _profile in recipients:
                    channels = CropCalendarNotificationService.preferences(_profile)["categories"]["important_alerts"]
                    if not (channels["in_app"] or channels["push"]):
                        continue
                    existing = FarmerNotification.query.filter_by(
                        user_id=user.id,
                        notification_type="regional_alert",
                        region=region,
                        title_en=f"Regional alert: {region}",
                        message_en=message_en,
                        message_am=message_am,
                    ).filter(FarmerNotification.created_at >= duplicate_cutoff).first()
                    if existing is not None:
                        continue
                    notification = FarmerNotification(user_id=user.id,
                        title_en=f"Regional alert: {region}", title_am=f"የክልል ማስጠንቀቂያ: {region}",
                        message_en=message_en, message_am=message_am, region=region,
                        notification_type="regional_alert",
                        discussion_post_id=posts[region].id)
                    db.session.add(notification)
                    app_notifications.append((notification, _profile))
                    app_notifications_created += 1
                db.session.commit()
                from backend.app.services.web_push_service import WebPushService

                for notification, _profile in app_notifications:
                    try:
                        WebPushService.enqueue_notification(notification)
                    except Exception:
                        db.session.rollback()
                        current_app.logger.exception(
                            "Could not enqueue regional push (farmer_id=%s).",
                            notification.user_id,
                        )
            except Exception:
                db.session.rollback()
                app_notifications_created = 0
                app_notifications = []
                app_notification_error = "Could not persist app notifications."
                current_app.logger.exception("Regional app notification persistence failed.")

        sms_recipients = [(region, user, profile) for region, user, profile in recipients
                          if profile.sms_opt_in and CropCalendarNotificationService.preferences(profile)["categories"]["important_alerts"]["sms"]]
        if method in {"sms", "both"}:
            for region, user, profile in sms_recipients:
                language = "am" if str(user.preferred_language).lower().startswith("am") else "en"
                sms_message = message_am if language == "am" else message_en
                try:
                    duplicate_sms = SMSRecord.query.filter_by(
                        user_id=user.id, notification_type="regional_alert",
                        message=sms_message, region=region,
                    ).filter(
                        SMSRecord.created_at >= duplicate_cutoff,
                        SMSRecord.status.in_(("sent", "submitted", "pending", "deferred")),
                    ).first()
                    if duplicate_sms is not None:
                        sms_duplicates_skipped += 1
                        continue
                    dedupe_key = "regional:{}:{}:{}:{}".format(
                        user.id, _region_key(region), datetime.now(timezone.utc).date().isoformat(),
                        hashlib.sha256(sms_message.encode("utf-8")).hexdigest()[:24],
                    )
                    if CropCalendarNotificationService.quiet_now(profile, critical=True):
                        SMSService.defer_sms(
                            user.phone_number, sms_message, user_id=user.id,
                            dedupe_key=dedupe_key, notification_type="regional_alert",
                            language=language, region=region, woreda=profile.woreda, kebele=profile.kebele,
                        )
                        sms_pending += 1
                        sms_results.append({"phone": user.phone_number, "status": "deferred", "error": None})
                        continue
                    result = SMSService.send_sms(recipient_phone=user.phone_number,
                        message=sms_message,
                        recipient_type="farmer", notification_type="regional_alert",
                        language=language, user_id=user.id, region=region,
                        woreda=profile.woreda, kebele=profile.kebele, dedupe_key=dedupe_key)
                    sms_results.append({
                        "phone": result.get("phone", user.phone_number),
                        "status": result.get("status", "failed"),
                        "provider_status": result.get("provider_status"),
                        "provider_status_code": result.get("provider_status_code"),
                        "provider_message_id": result.get("provider_message_id"),
                        "sms_record_id": result.get("sms_record_id"),
                        "error": "SMS delivery failed for this recipient." if result.get("error") else None,
                    })
                    if result.get("status") in {"sent", "submitted"}:
                        sms_accepted += 1
                    elif result.get("status") == "pending":
                        sms_pending += 1
                    else:
                        sms_failed += 1
                except Exception:
                    sms_failed += 1
                    db.session.rollback()
                    current_app.logger.exception("Regional SMS failed for a farmer (user_id=%s).", user.id)

        response_message = f"Alert processed for {len(recipients)} farmers."
        if app_notification_error:
            response_message = f"{response_message} {app_notification_error}"
        return jsonify({"success": True, "farmer_count": len(recipients),
            "sms_eligible_count": len(sms_recipients),
            "regions": regions, "method": method,
            "app_notifications_created": app_notifications_created,
            "app_notification_error": app_notification_error,
            "sms_accepted": sms_accepted,
            "sms_pending": sms_pending, "sms_failed": sms_failed,
            "sms_duplicates_skipped": sms_duplicates_skipped, "community_posts": len(posts),
            "sms_results": sms_results,
            "message": response_message}), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unexpected failure processing regional alert.")
        return jsonify({"success": False, "message": "Could not send the regional alert."}), 500


@regional_alert_bp.get("/farmer/notifications")
@jwt_required()
def list_farmer_notifications():
    user_id, error = _farmer_access()
    if error:
        return error
    try:
        profile = db.session.get(FarmerProfile, user_id)
        if profile is None:
            return jsonify({"notifications": []})
        from backend.app.services.crop_calendar_notification_service import (
            CropCalendarNotificationService,
        )

        visible_items = [
            item for item in FarmerNotification.query.filter_by(user_id=user_id).order_by(
                FarmerNotification.created_at.desc(), FarmerNotification.id.desc()
            ).all()
            if CropCalendarNotificationService.preferences(profile)["categories"][
                CropCalendarNotificationService.CATEGORY_MAP.get(item.notification_type, "important_alerts")
            ]["in_app"]
        ]
        farmer = db.session.get(User, user_id)
        language = "am" if str(farmer.preferred_language).lower().startswith("am") else "en"
        return jsonify({"notifications": [{"id": item.id,
            "title": item.title_am if language == "am" else item.title_en,
            "message": item.message_am if language == "am" else item.message_en,
            "region": item.region, "notification_type": item.notification_type,
            "outbreak_alert_id": item.outbreak_alert_id, "is_read": item.is_read,
            "discussion_post_id": item.discussion_post_id,
            "created_at": item.created_at.isoformat() if item.created_at else None} for item in visible_items]})
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to load farmer notifications (user_id=%s).", user_id)
        return jsonify({"success": False, "message": "Could not load notifications."}), 500


@regional_alert_bp.get("/farmer/notifications/unread-count")
@jwt_required()
def get_unread_notification_count():
    user_id, error = _farmer_access()
    if error:
        return error
    try:
        profile = db.session.get(FarmerProfile, user_id)
        if profile is None:
            return jsonify({"success": True, "count": 0})
        from backend.app.services.crop_calendar_notification_service import (
            CropCalendarNotificationService,
        )

        prefs = CropCalendarNotificationService.preferences(profile)
        unread_items = FarmerNotification.query.filter_by(
            user_id=user_id,
            is_read=False,
        ).all()
        count = sum(
            prefs["categories"][
                CropCalendarNotificationService.CATEGORY_MAP.get(
                    item.notification_type,
                    "important_alerts",
                )
            ]["in_app"]
            for item in unread_items
        )
        return jsonify({"success": True, "count": count})
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to count unread farmer notifications (user_id=%s).", user_id)
        return jsonify({"success": False, "message": "Could not load unread notification count."}), 500


@regional_alert_bp.patch("/farmer/notifications/<int:notification_id>/read")
@jwt_required()
def mark_notification_read(notification_id):
    user_id, error = _farmer_access()
    if error:
        return error
    try:
        item = FarmerNotification.query.filter_by(id=notification_id, user_id=user_id).first()
        if item is None:
            return jsonify({"success": False, "message": "Notification not found."}), 404
        if not item.is_read:
            item.is_read = True
            item.read_at = db.func.now()
            db.session.commit()
        return jsonify({"success": True, "notification": {"id": item.id, "is_read": True}})
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to mark notification read (user_id=%s, notification_id=%s).", user_id, notification_id)
        return jsonify({"success": False, "message": "Could not update notification."}), 500


@regional_alert_bp.patch("/farmer/notifications/read-all")
@jwt_required()
def mark_all_notifications_read():
    user_id, error = _farmer_access()
    if error:
        return error
    try:
        updated = FarmerNotification.query.filter_by(user_id=user_id, is_read=False).update({
            "is_read": True, "read_at": db.func.now(),
        }, synchronize_session=False)
        db.session.commit()
        return jsonify({"success": True, "updated": updated})
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to mark all farmer notifications read (user_id=%s).", user_id)
        return jsonify({"success": False, "message": "Could not update notifications."}), 500
