"""
=========================================================
Discussion & Agricultural Communication Routes
=========================================================

Provides communication between farmers and extension agents.

Post types:
    - question
    - advisory
    - announcement
    - alert

Farmers:
    - view posts
    - create questions
    - reply to posts

Extension agents:
    - view posts
    - create advisories, announcements, and alerts
    - reply to posts

Location targeting is supported for extension-agent posts.
=========================================================
"""

from __future__ import annotations

import io
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_from_directory, url_for
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from PIL import Image, UnidentifiedImageError

from backend.app.extensions import db
from backend.app.models import (
    DiscussionPost,
    DiscussionReply,
    DiscussionPostLike,
    DiagnosisRecord,
    FarmerProfile,
    User,
)
from backend.app.routes.auth import roles_required


discussion_bp = Blueprint(
    "discussion",
    __name__,
    url_prefix="/api/discussion",
)


# =========================================================
# Constants
# =========================================================

FARMER_POST_TYPES = {"question"}

EXTENSION_POST_TYPES = {
    "advisory",
    "announcement",
    "alert",
}

ALL_POST_TYPES = FARMER_POST_TYPES | EXTENSION_POST_TYPES

VALID_PRIORITIES = {
    "normal",
    "important",
    "urgent",
}

MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 10000
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
DISCUSSION_IMAGE_NAME = re.compile(r"^\d+_[a-f0-9]{32}\.(?:jpg|png|webp)$")


# =========================================================
# Response Helpers
# =========================================================

def success_response(data, status_code=200):
    return jsonify({
        "success": True,
        "data": data,
    }), status_code


def error_response(code, message, status_code):
    return jsonify({
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }), status_code


# =========================================================
# Authentication Helpers
# =========================================================

def _get_authenticated_user():
    """
    Return the currently authenticated active user.
    """

    identity = get_jwt_identity()

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    user = db.session.get(User, user_id)

    if user is None or not user.is_active:
        return None

    return user


def _get_user_role():
    """
    Get normalized role from the JWT claims.
    """

    claims = get_jwt()

    return str(
        claims.get("role", "")
    ).strip().lower()


# =========================================================
# Serialization
# =========================================================

def _serialize_post(post: DiscussionPost, current_user: User | None = None):
    author = post.author

    replies = sorted(
        post.replies,
        key=lambda reply: reply.created_at or datetime.min.replace(
            tzinfo=timezone.utc
        ),
    )

    author_profile = getattr(author, "extension_agent_profile", None) if author else None
    image_filename = Path(post.image_path).name if post.image_path else None
    image_url = None
    if image_filename and DISCUSSION_IMAGE_NAME.fullmatch(image_filename):
        image_url = url_for("discussion.serve_post_image", filename=image_filename)

    return {
        "id": post.id,
        "author_id": author.id if author else None,
        "author_name": author.full_name if author else None,
        "author_role": author.role if author else None,
        # The current schema stores certification numbers but has no reviewed
        # verification state, so a certification value alone must not earn a badge.
        "author_verified": False,
        "author": {
            "id": author.id if author else None,
            "full_name": author.full_name if author else None,
            "role": author.role if author else None,
        },
        "post_type": post.post_type,
        "title": post.title,
        "content": post.content,
        "image_path": post.image_path,
        "image_url": image_url,
        "diagnosis_id": post.diagnosis_id,
        "target_location": {
            "region": post.target_region,
            "woreda": post.target_woreda,
            "kebele": post.target_kebele,
        },
        "priority": post.priority,
        "reply_count": len(replies),
        "replies_count": len(replies),
        "likes_count": len(post.likes),
        "liked_by_current_user": bool(
            current_user and any(like.user_id == current_user.id for like in post.likes)
        ),
        "region": (
            author_profile.region if author_profile
            else getattr(getattr(author, "farmer_profile", None), "region", None)
        ) if author else None,
        "woreda": (
            author_profile.woreda if author_profile
            else getattr(getattr(author, "farmer_profile", None), "woreda", None)
        ) if author else None,
        "created_at": (
            post.created_at.isoformat()
            if post.created_at
            else None
        ),
        "updated_at": (
            post.updated_at.isoformat()
            if post.updated_at
            else None
        ),
    }


def _serialize_reply(reply: DiscussionReply):
    if reply.extension_agent_id is not None:
        author = reply.extension_agent
        author_role = "extension_agent"
    else:
        author = reply.farmer
        author_role = "farmer"

    return {
        "id": reply.id,
        "post_id": reply.post_id,
        "author_id": author.id if author else None,
        "author_name": author.full_name if author else None,
        "author": {
            "id": author.id if author else None,
            "full_name": author.full_name if author else None,
            "role": author_role,
        },
        "content": reply.content,
        "created_at": (
            reply.created_at.isoformat()
            if reply.created_at
            else None
        ),
        "updated_at": (
            reply.updated_at.isoformat()
            if reply.updated_at
            else None
        ),
    }


def _owned_post_or_error(post_id: int, user: User):
    post = db.session.get(DiscussionPost, post_id)
    if post is None:
        return None, error_response("NOT_FOUND", "Discussion post not found.", 404)
    if post.author_id != user.id:
        return None, error_response("FORBIDDEN", "You can only change your own posts.", 403)
    return post, None


def _post_visibility_error(post: DiscussionPost, user: User):
    """Keep detail and mutation access aligned with farmer feed visibility."""
    if user.role != "farmer":
        return None

    profile = FarmerProfile.query.filter_by(user_id=user.id).first()
    if post.target_region and (not profile or profile.region != post.target_region):
        return error_response("FORBIDDEN", "This post is not available for your region.", 403)
    if post.target_woreda and (not profile or profile.woreda != post.target_woreda):
        return error_response("FORBIDDEN", "This post is not available for your woreda.", 403)
    if post.target_kebele and (not profile or profile.kebele != post.target_kebele):
        return error_response("FORBIDDEN", "This post is not available for your kebele.", 403)
    return None


def _valid_owned_image(image_path: str | None, user: User) -> bool:
    if not image_path:
        return True
    filename = Path(image_path).name
    if not filename.startswith(f"{user.id}_") or not DISCUSSION_IMAGE_NAME.fullmatch(filename):
        return False
    return (Path(current_app.config["UPLOAD_DIR"]) / "community" / filename).is_file()


# =========================================================
# Location Helpers
# =========================================================

def _normalize_location(value):
    """
    Normalize optional location values.

    Empty strings are converted to None.
    """

    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def _validate_extension_targeting(data):
    """
    Validate location targeting supplied by an extension agent.

    A lower-level location requires the higher-level location.

    Examples:
        kebele requires woreda and region
        woreda requires region
    """

    region = _normalize_location(data.get("target_region"))
    woreda = _normalize_location(data.get("target_woreda"))
    kebele = _normalize_location(data.get("target_kebele"))

    if woreda and not region:
        return None, None, (
            "INVALID_LOCATION",
            "target_region is required when target_woreda is provided.",
        )

    if kebele and not woreda:
        return None, None, (
            "INVALID_LOCATION",
            "target_woreda is required when target_kebele is provided.",
        )

    return (
        region,
        woreda,
        kebele,
    ), None, None


# =========================================================
# Create Post
# =========================================================

@discussion_bp.route("/posts", methods=["POST"])
@jwt_required()
@roles_required("farmer", "extension_agent", "admin")
def create_post():
    """
    Create a farmer question or extension-agent communication post.
    """

    user = _get_authenticated_user()

    if user is None:
        return error_response(
            "UNAUTHORIZED",
            "Authenticated user was not found or is inactive.",
            401,
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "INVALID_REQUEST",
            "Request body must be a JSON object.",
            400,
        )

    post_type = str(
        data.get("post_type", "")
    ).strip().lower()

    title = str(
        data.get("title", "")
    ).strip()

    content = str(
        data.get("content", "")
    ).strip()

    if not post_type:
        return error_response(
            "VALIDATION_ERROR",
            "post_type is required.",
            400,
        )

    if post_type not in ALL_POST_TYPES:
        return error_response(
            "INVALID_POST_TYPE",
            (
                "post_type must be one of: "
                "question, advisory, announcement, alert."
            ),
            400,
        )

    if user.role == "farmer" and post_type not in FARMER_POST_TYPES:
        return error_response(
            "FORBIDDEN",
            "Farmers can only create question posts.",
            403,
        )

    if (
        user.role == "extension_agent"
        and post_type not in EXTENSION_POST_TYPES
    ):
        return error_response(
            "FORBIDDEN",
            (
                "Extension agents can create advisory, "
                "announcement, or alert posts."
            ),
            403,
        )

    if not title:
        return error_response(
            "VALIDATION_ERROR",
            "title is required.",
            400,
        )

    if len(title) > MAX_TITLE_LENGTH:
        return error_response(
            "VALIDATION_ERROR",
            f"title cannot exceed {MAX_TITLE_LENGTH} characters.",
            400,
        )

    if not content:
        return error_response(
            "VALIDATION_ERROR",
            "content is required.",
            400,
        )

    if len(content) > MAX_CONTENT_LENGTH:
        return error_response(
            "VALIDATION_ERROR",
            f"content cannot exceed {MAX_CONTENT_LENGTH} characters.",
            400,
        )

    image_path = _normalize_location(
        data.get("image_path")
    )

    if not _valid_owned_image(image_path, user):
        return error_response(
            "INVALID_IMAGE",
            "Choose an image uploaded by your account.",
            400,
        )

    diagnosis_id = data.get("diagnosis_id")

    if diagnosis_id is not None:
        try:
            diagnosis_id = int(diagnosis_id)
        except (TypeError, ValueError):
            return error_response(
                "VALIDATION_ERROR",
                "diagnosis_id must be an integer.",
                400,
            )

        diagnosis = db.session.get(
            DiagnosisRecord,
            diagnosis_id,
        )

        if diagnosis is None:
            return error_response(
                "NOT_FOUND",
                "The specified diagnosis was not found.",
                404,
            )

        # A farmer may only link their own diagnosis.
        if user.role == "farmer" and diagnosis.user_id != user.id:
            return error_response(
                "FORBIDDEN",
                "You can only link your own diagnosis.",
                403,
            )

    priority = str(
        data.get("priority", "normal")
    ).strip().lower()

    if priority not in VALID_PRIORITIES:
        return error_response(
            "INVALID_PRIORITY",
            "priority must be normal, important, or urgent.",
            400,
        )

    target_region = None
    target_woreda = None
    target_kebele = None

    if user.role == "extension_agent":
        location_result, _, location_error = (
            _validate_extension_targeting(data)
        )

        if location_error:
            code, message = location_error

            return error_response(
                code,
                message,
                400,
            )

        (
            target_region,
            target_woreda,
            target_kebele,
        ) = location_result

    else:
        # Farmers do not define the audience of their question.
        target_region = None
        target_woreda = None
        target_kebele = None

    post = DiscussionPost(
        author_id=user.id,
        post_type=post_type,
        title=title,
        content=content,
        image_path=image_path,
        diagnosis_id=diagnosis_id,
        target_region=target_region,
        target_woreda=target_woreda,
        target_kebele=target_kebele,
        priority=priority,
    )

    db.session.add(post)
    db.session.commit()

    return success_response(
        _serialize_post(post, user),
        201,
    )


# =========================================================
# List Posts
# =========================================================

@discussion_bp.route("/posts", methods=["GET"])
@jwt_required()
@roles_required("farmer", "extension_agent", "admin")
def list_posts():
    """
    List discussion posts.

    Supports:
        page
        per_page
        search
        post_type
        priority
    """

    user = _get_authenticated_user()

    if user is None:
        return error_response(
            "UNAUTHORIZED",
            "Authenticated user was not found or is inactive.",
            401,
        )

    try:
        page = max(
            int(request.args.get("page", 1)),
            1,
        )
    except (TypeError, ValueError):
        return error_response(
            "VALIDATION_ERROR",
            "page must be an integer.",
            400,
        )

    try:
        per_page = int(
            request.args.get("per_page", 20)
        )
    except (TypeError, ValueError):
        return error_response(
            "VALIDATION_ERROR",
            "per_page must be an integer.",
            400,
        )

    per_page = min(
        max(per_page, 1),
        100,
    )

    search = request.args.get(
        "search",
        "",
    ).strip()

    post_type = request.args.get(
        "post_type",
        "",
    ).strip().lower()

    priority = request.args.get(
        "priority",
        "",
    ).strip().lower()
    mine = request.args.get("mine", "false").strip().lower() in {"1", "true", "yes"}

    query = DiscussionPost.query

    if mine:
        query = query.filter(DiscussionPost.author_id == user.id)

    if search:
        pattern = f"%{search}%"

        query = query.filter(
            or_(
                DiscussionPost.title.ilike(pattern),
                DiscussionPost.content.ilike(pattern),
            )
        )

    if post_type:
        if post_type not in ALL_POST_TYPES:
            return error_response(
                "INVALID_POST_TYPE",
                "Invalid post_type filter.",
                400,
            )

        query = query.filter(
            DiscussionPost.post_type == post_type
        )

    if priority:
        if priority not in VALID_PRIORITIES:
            return error_response(
                "INVALID_PRIORITY",
                "Invalid priority filter.",
                400,
            )

        query = query.filter(
            DiscussionPost.priority == priority
        )

    # Farmers should see:
    #   1. general posts
    #   2. extension posts targeted to their location
    #
    # Extension agents can see all posts.
    if user.role == "farmer":
        profile = FarmerProfile.query.filter_by(
            user_id=user.id
        ).first()

        if profile:
            location_filters = [
                DiscussionPost.target_region.is_(None),
            ]

            if profile.region:
                location_filters.append(
                    DiscussionPost.target_region == profile.region
                )

            query = query.filter(
                or_(*location_filters)
            )

            # Woreda/kebele refinement is handled below
            # only for targeted extension posts.
            if profile.region:
                query = query.filter(
                    or_(
                        DiscussionPost.target_region.is_(None),
                        DiscussionPost.target_region == profile.region,
                    )
                )

                if profile.woreda:
                    query = query.filter(
                        or_(
                            DiscussionPost.target_woreda.is_(None),
                            DiscussionPost.target_woreda == profile.woreda,
                        )
                    )

                if profile.kebele:
                    query = query.filter(
                        or_(
                            DiscussionPost.target_kebele.is_(None),
                            DiscussionPost.target_kebele == profile.kebele,
                        )
                    )

        else:
            # Without a farmer profile, only general posts
            # are visible.
            query = query.filter(
                DiscussionPost.target_region.is_(None),
                DiscussionPost.target_woreda.is_(None),
                DiscussionPost.target_kebele.is_(None),
            )

    pagination = query.order_by(
        DiscussionPost.created_at.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )

    posts = [
        _serialize_post(post, user)
        for post in pagination.items
    ]

    return success_response({
        "items": posts,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_previous": pagination.has_prev,
        },
    })


# =========================================================
# Get Single Post
# =========================================================

@discussion_bp.route(
    "/posts/<int:post_id>",
    methods=["GET"],
)
@jwt_required()
@roles_required("farmer", "extension_agent", "admin")
def get_post(post_id):
    """
    Return one discussion post with all replies.
    """

    user = _get_authenticated_user()

    if user is None:
        return error_response(
            "UNAUTHORIZED",
            "Authenticated user was not found or is inactive.",
            401,
        )

    post = db.session.get(
        DiscussionPost,
        post_id,
    )

    if post is None:
        return error_response(
            "NOT_FOUND",
            "Discussion post not found.",
            404,
        )

    visibility_error = _post_visibility_error(post, user)
    if visibility_error:
        return visibility_error

    response = _serialize_post(post, user)

    response["replies"] = [
        _serialize_reply(reply)
        for reply in sorted(
            post.replies,
            key=lambda item: (
                item.created_at
                or datetime.min.replace(
                    tzinfo=timezone.utc
                )
            ),
        )
    ]

    return success_response(response)


# =========================================================
# Create Reply
# =========================================================

@discussion_bp.route(
    "/posts/<int:post_id>/replies",
    methods=["POST"],
)
@jwt_required()
@roles_required("farmer", "extension_agent")
def create_reply(post_id):
    """
    Add a farmer or extension-agent reply.
    """

    user = _get_authenticated_user()

    if user is None:
        return error_response(
            "UNAUTHORIZED",
            "Authenticated user was not found or is inactive.",
            401,
        )

    post = db.session.get(
        DiscussionPost,
        post_id,
    )

    if post is None:
        return error_response(
            "NOT_FOUND",
            "Discussion post not found.",
            404,
        )

    visibility_error = _post_visibility_error(post, user)
    if visibility_error:
        return visibility_error

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "INVALID_REQUEST",
            "Request body must be a JSON object.",
            400,
        )

    content = str(
        data.get("content", "")
    ).strip()

    if not content:
        return error_response(
            "VALIDATION_ERROR",
            "content is required.",
            400,
        )

    if len(content) > MAX_CONTENT_LENGTH:
        return error_response(
            "VALIDATION_ERROR",
            f"content cannot exceed {MAX_CONTENT_LENGTH} characters.",
            400,
        )

    reply = DiscussionReply(
        post_id=post.id,
        content=content,
    )

    if user.role == "farmer":
        reply.farmer_id = user.id
    else:
        reply.extension_agent_id = user.id

    db.session.add(reply)
    db.session.commit()

    return success_response(
        _serialize_reply(reply),
        201,
    )


@discussion_bp.route("/posts/<int:post_id>", methods=["PATCH"])
@jwt_required()
@roles_required("farmer", "extension_agent", "admin")
def update_post(post_id):
    user = _get_authenticated_user()
    if user is None:
        return error_response("UNAUTHORIZED", "Authenticated user was not found or is inactive.", 401)
    post, error = _owned_post_or_error(post_id, user)
    if error:
        return error

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response("INVALID_REQUEST", "Request body must be a JSON object.", 400)

    if "title" in data:
        title = str(data["title"]).strip()
        if not title or len(title) > MAX_TITLE_LENGTH:
            return error_response("VALIDATION_ERROR", f"title must be between 1 and {MAX_TITLE_LENGTH} characters.", 400)
        post.title = title
    if "content" in data:
        content = str(data["content"]).strip()
        if not content or len(content) > MAX_CONTENT_LENGTH:
            return error_response("VALIDATION_ERROR", f"content must be between 1 and {MAX_CONTENT_LENGTH} characters.", 400)
        post.content = content
    if "image_path" in data:
        image_path = _normalize_location(data.get("image_path"))
        if not _valid_owned_image(image_path, user):
            return error_response("INVALID_IMAGE", "Choose an image uploaded by your account.", 400)
        post.image_path = image_path

    db.session.commit()
    return success_response(_serialize_post(post, user))


@discussion_bp.route("/posts/<int:post_id>", methods=["DELETE"])
@jwt_required()
@roles_required("farmer", "extension_agent", "admin")
def delete_post(post_id):
    user = _get_authenticated_user()
    if user is None:
        return error_response("UNAUTHORIZED", "Authenticated user was not found or is inactive.", 401)
    post, error = _owned_post_or_error(post_id, user)
    if error:
        return error

    image_path = post.image_path
    db.session.delete(post)
    db.session.commit()
    if image_path:
        filename = Path(image_path).name
        if DISCUSSION_IMAGE_NAME.fullmatch(filename):
            upload_dir = Path(current_app.config["UPLOAD_DIR"]) / "community"
            try:
                (upload_dir / filename).unlink(missing_ok=True)
            except OSError:
                current_app.logger.warning("Could not remove discussion image %s", filename)
    return success_response({"deleted": True, "id": post_id})


@discussion_bp.route("/posts/<int:post_id>/like", methods=["POST"])
@jwt_required()
@roles_required("farmer", "extension_agent", "admin")
def like_post(post_id):
    user = _get_authenticated_user()
    if user is None:
        return error_response("UNAUTHORIZED", "Authenticated user was not found or is inactive.", 401)
    post = db.session.get(DiscussionPost, post_id)
    if post is None:
        return error_response("NOT_FOUND", "Discussion post not found.", 404)
    visibility_error = _post_visibility_error(post, user)
    if visibility_error:
        return visibility_error

    like = DiscussionPostLike.query.filter_by(post_id=post.id, user_id=user.id).first()
    if like is None:
        db.session.add(DiscussionPostLike(post_id=post.id, user_id=user.id))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    count = DiscussionPostLike.query.filter_by(post_id=post.id).count()
    return success_response({"liked": True, "likes_count": count})


@discussion_bp.route("/posts/<int:post_id>/like", methods=["DELETE"])
@jwt_required()
@roles_required("farmer", "extension_agent", "admin")
def unlike_post(post_id):
    user = _get_authenticated_user()
    if user is None:
        return error_response("UNAUTHORIZED", "Authenticated user was not found or is inactive.", 401)
    post = db.session.get(DiscussionPost, post_id)
    if post is None:
        return error_response("NOT_FOUND", "Discussion post not found.", 404)
    visibility_error = _post_visibility_error(post, user)
    if visibility_error:
        return visibility_error

    like = DiscussionPostLike.query.filter_by(post_id=post.id, user_id=user.id).first()
    if like is not None:
        db.session.delete(like)
        db.session.commit()
    count = DiscussionPostLike.query.filter_by(post_id=post.id).count()
    return success_response({"liked": False, "likes_count": count})


@discussion_bp.route("/posts/images", methods=["POST"])
@jwt_required()
@roles_required("farmer", "extension_agent", "admin")
def upload_post_image():
    user = _get_authenticated_user()
    if user is None:
        return error_response("UNAUTHORIZED", "Authenticated user was not found or is inactive.", 401)
    upload = request.files.get("image")
    if upload is None:
        return error_response("IMAGE_REQUIRED", "Choose an image to upload.", 400)

    content = upload.stream.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        return error_response("INVALID_IMAGE", "Images must be smaller than 5 MB.", 400)
    try:
        with Image.open(io.BytesIO(content)) as check_image:
            image_format = check_image.format
            width, height = check_image.size
            check_image.verify()
        if image_format not in IMAGE_FORMATS or width * height > MAX_IMAGE_PIXELS:
            return error_response("INVALID_IMAGE", "Use a valid JPG, PNG, or WEBP image under 20 megapixels.", 400)

        with Image.open(io.BytesIO(content)) as source:
            source.load()
            if image_format == "JPEG":
                output_image = source.convert("RGB")
            else:
                output_image = source.copy()
            output = io.BytesIO()
            output_image.save(output, format=image_format, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError):
        return error_response("INVALID_IMAGE", "The uploaded file is not a valid supported image.", 400)

    filename = f"{user.id}_{uuid.uuid4().hex}.{IMAGE_FORMATS[image_format]}"
    upload_dir = Path(current_app.config["UPLOAD_DIR"]) / "community"
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / filename).write_bytes(output.getvalue())
    return success_response({
        "image_path": filename,
        "image_url": url_for("discussion.serve_post_image", filename=filename),
    }, 201)


@discussion_bp.route("/posts/images/<filename>", methods=["GET"])
def serve_post_image(filename):
    if not DISCUSSION_IMAGE_NAME.fullmatch(filename):
        return error_response("NOT_FOUND", "Community image not found.", 404)
    upload_dir = Path(current_app.config["UPLOAD_DIR"]) / "community"
    if not (upload_dir / filename).is_file():
        return error_response("NOT_FOUND", "Community image not found.", 404)
    return send_from_directory(upload_dir, filename, conditional=True, max_age=3600)
