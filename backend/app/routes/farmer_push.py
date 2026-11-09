"""Authenticated farmer endpoints for managing this account's Web Push devices."""
from __future__ import annotations

import base64
import re
from urllib.parse import urlsplit

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models import FarmerPushSubscription, User
from backend.app.services.web_push_service import WebPushService

farmer_push_bp = Blueprint("farmer_push", __name__, url_prefix="/api/farmer/push")
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")
_PUSH_SERVICE_HOSTS = (
    "fcm.googleapis.com",
    "web.push.apple.com",
    "push.services.mozilla.com",
    "notify.windows.com",
)


def _farmer_id():
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


def _valid_key(
    value,
    *,
    expected_length=None,
    minimum_length=None,
    maximum_characters=200,
) -> bool:
    if (
        not isinstance(value, str)
        or len(value) > maximum_characters
        or not _BASE64URL.fullmatch(value)
    ):
        return False
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error):
        return False
    if expected_length is not None and len(decoded) != expected_length:
        return False
    return minimum_length is None or len(decoded) >= minimum_length


def _valid_p256dh(value) -> bool:
    if not _valid_key(value, expected_length=65):
        return False
    decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    return decoded[0] == 4


def _valid_endpoint(value) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").casefold().rstrip(".")
        known_push_service = any(
            hostname == host or hostname.endswith(f".{host}")
            for host in _PUSH_SERVICE_HOSTS
        )
        return (
            parsed.scheme == "https"
            and known_push_service
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment
        )
    except ValueError:
        return False


@farmer_push_bp.get("/config")
@jwt_required()
def get_push_config():
    user_id, error = _farmer_id()
    if error:
        return error
    configured = WebPushService.is_configured()
    return jsonify({
        "enabled": configured,
        "public_key": current_app.config["WEB_PUSH_VAPID_PUBLIC_KEY"] if configured else None,
    })


@farmer_push_bp.post("/subscriptions")
@jwt_required()
def save_push_subscription():
    user_id, error = _farmer_id()
    if error:
        return error
    if not WebPushService.is_configured():
        return jsonify({"success": False, "message": "Web Push is not configured."}), 503
    data = request.get_json(silent=True)
    keys = data.get("keys") if isinstance(data, dict) else None
    endpoint = data.get("endpoint") if isinstance(data, dict) else None
    if (
        not isinstance(data, dict)
        or not _valid_endpoint(endpoint)
        or not isinstance(keys, dict)
        or not _valid_p256dh(keys.get("p256dh"))
        or not _valid_key(
            keys.get("auth"),
            minimum_length=16,
            maximum_characters=100,
        )
    ):
        return jsonify({"success": False, "message": "Push subscription is invalid."}), 400

    subscription = FarmerPushSubscription.query.filter_by(endpoint=endpoint).first()
    if subscription is not None and subscription.user_id != user_id:
        return jsonify({"success": False, "message": "This device subscription is already associated with another account."}), 409
    if subscription is None:
        subscription = FarmerPushSubscription(user_id=user_id, endpoint=endpoint)
        db.session.add(subscription)
    subscription.p256dh = keys["p256dh"]
    subscription.auth = keys["auth"]
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "message": "Push subscription could not be saved."}), 409
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not save farmer push subscription (user_id=%s).", user_id)
        return jsonify({"success": False, "message": "Push subscription could not be saved."}), 500
    return jsonify({"success": True}), 201


@farmer_push_bp.delete("/subscriptions")
@jwt_required()
def remove_push_subscription():
    user_id, error = _farmer_id()
    if error:
        return error
    data = request.get_json(silent=True)
    endpoint = data.get("endpoint") if isinstance(data, dict) else None
    if not _valid_endpoint(endpoint):
        return jsonify({"success": False, "message": "A valid push endpoint is required."}), 400
    subscription = FarmerPushSubscription.query.filter_by(
        user_id=user_id,
        endpoint=endpoint,
    ).first()
    if subscription is not None:
        db.session.delete(subscription)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Could not remove farmer push subscription (user_id=%s).", user_id)
            return jsonify({"success": False, "message": "Push subscription could not be removed."}), 500
    return jsonify({"success": True, "removed": subscription is not None})
