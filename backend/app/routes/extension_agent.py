"""
=========================================================
Extension Agent API Routes
=========================================================

Provides authenticated agricultural extension agents with
the ability to:

    - Review farmer AI diagnosis records.
    - View one diagnosis in detail.
    - Provide professional expert comments.

Endpoints:
    GET  /api/extension-agent/diagnoses
    GET  /api/extension-agent/diagnoses/<diagnosis_id>
    POST /api/extension-agent/diagnoses/<diagnosis_id>/comments

Access:
    extension_agent role only.
=========================================================
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from backend.app.extensions import db
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.extension_comment import ExtensionComment
from backend.app.models.user import User


# =========================================================
# BLUEPRINT
# =========================================================

extension_agent_bp = Blueprint(
    "extension_agent",
    __name__,
    url_prefix="/api/extension-agent",
)


# =========================================================
# AUTHORIZATION HELPER
# =========================================================

def _require_extension_agent():
    """
    Verify that the authenticated user is an extension agent.

    Returns:
        User object if authorized.
        Flask response tuple if unauthorized.
    """

    claims = get_jwt()

    role = str(
        claims.get("role", "")
    ).strip().lower()

    if role != "extension_agent":
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "FORBIDDEN",
                        "message": (
                            "Only extension agents can "
                            "access this resource."
                        ),
                    },
                }
            ),
            403,
        )

    identity = get_jwt_identity()

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_USER_ID",
                        "message": (
                            "Authenticated user identity "
                            "is invalid."
                        ),
                    },
                }
            ),
            401,
        )

    user = User.query.get(user_id)

    if user is None:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": (
                            "Extension agent account "
                            "was not found."
                        ),
                    },
                }
            ),
            404,
        )

    if not user.is_active:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INACTIVE_ACCOUNT",
                        "message": (
                            "This extension agent "
                            "account is inactive."
                        ),
                    },
                }
            ),
            403,
        )

    return user, None


# =========================================================
# SERIALIZATION
# =========================================================

def _serialize_comment(
    comment: ExtensionComment,
) -> dict:
    """
    Convert an ExtensionComment into JSON-safe data.
    """

    agent = comment.extension_agent

    return {
        "id": comment.id,
        "diagnosis_id": comment.diagnosis_id,
        "extension_agent": {
            "id": agent.id if agent else None,
            "full_name": (
                agent.full_name
                if agent
                else None
            ),
        },
        "comment": comment.comment,
        "created_at": (
            comment.created_at.isoformat()
            if comment.created_at
            else None
        ),
        "updated_at": (
            comment.updated_at.isoformat()
            if comment.updated_at
            else None
        ),
    }


def _serialize_diagnosis(
    diagnosis: DiagnosisRecord,
) -> dict:
    """
    Convert a diagnosis record into data suitable for
    extension-agent review.
    """

    farmer = diagnosis.user

    comments = sorted(
        diagnosis.extension_comments,
        key=lambda item: item.created_at,
    )

    return {
        "id": diagnosis.id,
        "farmer": {
            "id": farmer.id if farmer else None,
            "full_name": (
                farmer.full_name
                if farmer
                else None
            ),
            "phone_number": (
                farmer.phone_number
                if farmer
                else None
            ),
        },
        "image_filename": diagnosis.image_filename,
        "image_path": diagnosis.image_path,
        "disease_class": diagnosis.disease_class,
        "confidence": diagnosis.confidence,
        "model_name": diagnosis.model_name,
        "model_version": diagnosis.model_version,
        "prediction_time": diagnosis.prediction_time,
        "explainability_requested": (
            diagnosis.explainability_requested
        ),
        "heatmap_path": diagnosis.heatmap_path,
        "created_at": (
            diagnosis.created_at.isoformat()
            if diagnosis.created_at
            else None
        ),
        "extension_comments": [
            _serialize_comment(comment)
            for comment in comments
        ],
    }


# =========================================================
# LIST DIAGNOSES
# =========================================================

@extension_agent_bp.get("/diagnoses")
@jwt_required()
def list_diagnoses():
    """
    Return farmer diagnosis records for extension-agent
    review.

    Query parameters:
        page
        per_page
    """

    agent, error = _require_extension_agent()

    if error is not None:
        return error

    try:
        page = request.args.get(
            "page",
            default=1,
            type=int,
        )

        per_page = request.args.get(
            "per_page",
            default=20,
            type=int,
        )

        page = max(page, 1)
        per_page = min(max(per_page, 1), 100)

        pagination = (
            DiagnosisRecord.query
            .order_by(
                DiagnosisRecord.created_at.desc()
            )
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False,
            )
        )

        diagnoses = [
            _serialize_diagnosis(record)
            for record in pagination.items
        ]

        return jsonify(
            {
                "success": True,
                "data": {
                    "diagnoses": diagnoses,
                    "pagination": {
                        "page": pagination.page,
                        "per_page": pagination.per_page,
                        "total": pagination.total,
                        "pages": pagination.pages,
                        "has_next": pagination.has_next,
                        "has_previous": (
                            pagination.has_prev
                        ),
                    },
                },
            }
        ), 200

    except Exception:
        db.session.rollback()

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "DIAGNOSIS_LIST_ERROR",
                    "message": (
                        "Unable to retrieve diagnosis "
                        "records."
                    ),
                },
            }
        ), 500


# =========================================================
# GET ONE DIAGNOSIS
# =========================================================

@extension_agent_bp.get(
    "/diagnoses/<int:diagnosis_id>"
)
@jwt_required()
def get_diagnosis(diagnosis_id: int):
    """
    Return one diagnosis for extension-agent review.
    """

    agent, error = _require_extension_agent()

    if error is not None:
        return error

    diagnosis = DiagnosisRecord.query.get(
        diagnosis_id
    )

    if diagnosis is None:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "DIAGNOSIS_NOT_FOUND",
                    "message": (
                        "Diagnosis record was not found."
                    ),
                },
            }
        ), 404

    return jsonify(
        {
            "success": True,
            "data": {
                "diagnosis": _serialize_diagnosis(
                    diagnosis
                ),
            },
        }
    ), 200


# =========================================================
# ADD EXPERT COMMENT
# =========================================================

@extension_agent_bp.post(
    "/diagnoses/<int:diagnosis_id>/comments"
)
@jwt_required()
def add_comment(diagnosis_id: int):
    """
    Add an expert comment to a farmer diagnosis.
    """

    agent, error = _require_extension_agent()

    if error is not None:
        return error

    diagnosis = DiagnosisRecord.query.get(
        diagnosis_id
    )

    if diagnosis is None:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "DIAGNOSIS_NOT_FOUND",
                    "message": (
                        "Diagnosis record was not found."
                    ),
                },
            }
        ), 404

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": (
                        "Request body must contain "
                        "valid JSON."
                    ),
                },
            }
        ), 400

    comment_text = data.get("comment")

    if not isinstance(comment_text, str):
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "INVALID_COMMENT",
                    "message": (
                        "Comment must be a string."
                    ),
                },
            }
        ), 400

    comment_text = comment_text.strip()

    if not comment_text:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "EMPTY_COMMENT",
                    "message": (
                        "Comment cannot be empty."
                    ),
                },
            }
        ), 400

    if len(comment_text) > 5000:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "COMMENT_TOO_LONG",
                    "message": (
                        "Comment must not exceed "
                        "5000 characters."
                    ),
                },
            }
        ), 400

    try:
        comment = ExtensionComment(
            diagnosis_id=diagnosis.id,
            extension_agent_id=agent.id,
            comment=comment_text,
        )

        db.session.add(comment)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "data": {
                    "message": (
                        "Expert comment added "
                        "successfully."
                    ),
                    "comment": _serialize_comment(
                        comment
                    ),
                },
            }
        ), 201

    except Exception:
        db.session.rollback()

        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "COMMENT_CREATE_ERROR",
                    "message": (
                        "Unable to save expert comment."
                    ),
                },
            }
        ), 500