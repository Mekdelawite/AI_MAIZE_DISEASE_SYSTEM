"""Admin broadcast alerts to farmers by region."""
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from backend.app.extensions import db
from backend.app.models import DiscussionPost, FarmerNotification, FarmerProfile, User
from backend.app.services.sms_service import SMSService

regional_alert_bp = Blueprint("regional_alert", __name__, url_prefix="/api")

REGIONS = {
    "oromia", "amhara", "snnpr", "sidama", "south west ethiopia", "tigray",
    "benishangul-gumuz", "gambela", "somali", "afar", "harari", "dire dawa", "addis ababa",
}


def _region_key(value):
    return " ".join(str(value or "").casefold().split())


@regional_alert_bp.post("/admin/regional-alerts")
@jwt_required()
def send_regional_alert():
    if str(get_jwt().get("role", "")).lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403
    data = request.get_json(silent=True) or {}
    regions = list(dict.fromkeys(str(r).strip() for r in data.get("regions", []) if str(r).strip()))
    message_en = str(data.get("message_en", "")).strip()
    message_am = str(data.get("message_am", "")).strip()
    method = str(data.get("method", "")).lower()
    if not regions or any(_region_key(region) not in REGIONS for region in regions):
        return jsonify({"success": False, "message": "Select one or more valid Ethiopian regions."}), 400
    if not message_en or not message_am or len(message_en) > 5000 or len(message_am) > 5000:
        return jsonify({"success": False, "message": "Enter both messages (up to 5,000 characters each)."}), 400
    if method not in {"sms", "app", "both"}:
        return jsonify({"success": False, "message": "Delivery method must be sms, app, or both."}), 400

    recipient_rows = (db.session.query(User, FarmerProfile)
        .join(FarmerProfile, FarmerProfile.user_id == User.id)
        .filter(User.role == "farmer", User.is_active.is_(True))
        .all())
    recipients_by_region = {region: [(user, profile) for user, profile in recipient_rows
        if _region_key(profile.region) == _region_key(region)] for region in regions}
    recipients = [(region, user, profile) for region, pairs in recipients_by_region.items()
        for user, profile in pairs]
    if not recipients:
        return jsonify({"success": True, "code": "NO_FARMERS", "message": "No farmers registered in this region.", "farmer_count": 0}), 200

    admin_id = int(get_jwt_identity())
    posts = {}
    sms_accepted = sms_pending = sms_failed = 0
    sms_results = []
    try:
        if method in {"app", "both"}:
            for region, pairs in recipients_by_region.items():
                if not pairs:
                    continue
                post = DiscussionPost(author_id=admin_id, post_type="alert",
                    title=f"Regional alert: {region}",
                    content=f"English:\n{message_en}\n\nአማርኛ:\n{message_am}",
                    target_region=region, priority="urgent")
                db.session.add(post)
                db.session.flush()
                posts[region] = post
            for region, user, _profile in recipients:
                db.session.add(FarmerNotification(user_id=user.id,
                    title_en=f"Regional alert: {region}", title_am=f"የክልል ማስጠንቀቂያ: {region}",
                    message_en=message_en, message_am=message_am, region=region,
                    discussion_post_id=posts[region].id))
            db.session.commit()

        if method in {"sms", "both"}:
            for region, user, profile in recipients:
                language = "am" if str(user.preferred_language).lower().startswith("am") else "en"
                try:
                    result = SMSService.send_sms(recipient_phone=user.phone_number,
                        message=message_am if language == "am" else message_en,
                        recipient_type="farmer", notification_type="regional_alert",
                        language=language, user_id=user.id, region=region,
                        woreda=profile.woreda, kebele=profile.kebele)
                    sms_results.append({
                        "phone": result.get("phone", user.phone_number),
                        "status": result.get("status", "failed"),
                        "provider_status": result.get("provider_status"),
                        "provider_status_code": result.get("provider_status_code"),
                        "provider_message_id": result.get("provider_message_id"),
                        "sms_record_id": result.get("sms_record_id"),
                        "error": result.get("error"),
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

        return jsonify({"success": True, "farmer_count": len(recipients),
            "regions": regions, "method": method, "sms_accepted": sms_accepted,
            "sms_pending": sms_pending, "sms_failed": sms_failed, "community_posts": len(posts),
            "sms_results": sms_results,
            "message": f"Alert processed for {len(recipients)} farmers."}), 201
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Could not send the regional alert."}), 500


@regional_alert_bp.get("/farmer/notifications")
@jwt_required()
def list_farmer_notifications():
    if str(get_jwt().get("role", "")).lower() != "farmer":
        return jsonify({"success": False, "message": "Farmer access required."}), 403
    user_id = int(get_jwt_identity())
    items = FarmerNotification.query.filter_by(user_id=user_id).order_by(FarmerNotification.created_at.desc()).limit(30).all()
    farmer = db.session.get(User, user_id)
    language = "am" if farmer and str(farmer.preferred_language).lower().startswith("am") else "en"
    return jsonify({"notifications": [{"id": item.id,
        "title": item.title_am if language == "am" else item.title_en,
        "message": item.message_am if language == "am" else item.message_en,
        "region": item.region, "is_read": item.is_read,
        "discussion_post_id": item.discussion_post_id,
        "created_at": item.created_at.isoformat()} for item in items]})
