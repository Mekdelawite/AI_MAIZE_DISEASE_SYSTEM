
"""
=========================================================
Administrative Report Routes
=========================================================

API endpoints for generating administrative reports.

Supported formats:
    - PDF
    - CSV

Access:
    - Administrator only

Business logic is delegated to ReportService.
=========================================================
"""

from __future__ import annotations

from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required

from backend.app.routes.auth import error_response, roles_required
from backend.app.services.admin_service import InvalidDateFilterError
from backend.app.services.report_service import (
    ReportService,
    ReportServiceError,
)


report_bp = Blueprint(
    "report",
    __name__,
    url_prefix="/api/admin/reports",
)


def _get_report_filters() -> dict[str, str | None]:
    """
    Read optional report filters from the query string.

    Supported filters:
        disease_class
        start_date
        end_date
    """

    disease_class = request.args.get(
        "disease_class",
        default=None,
        type=str,
    )

    start_date = request.args.get(
        "start_date",
        default=None,
        type=str,
    )

    end_date = request.args.get(
        "end_date",
        default=None,
        type=str,
    )

    return {
        "disease_class": disease_class,
        "start_date": start_date,
        "end_date": end_date,
    }


# =========================================================
# PDF REPORT
# =========================================================

@report_bp.get("/pdf")
@jwt_required()
@roles_required("admin")
def generate_pdf_report():
    """
    Generate and return an administrative PDF report.

    Optional query parameters:
        disease_class
        start_date
        end_date
    """

    filters = _get_report_filters()

    try:
        pdf_file = ReportService.generate_pdf(
            disease_class=filters["disease_class"],
            start_date=filters["start_date"],
            end_date=filters["end_date"],
        )

        return send_file(
            pdf_file,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="maize_admin_report.pdf",
        )

    except InvalidDateFilterError as exc:
        return error_response(
            "INVALID_DATE_FILTER",
            str(exc),
            400,
        )

    except ReportServiceError:
        return error_response(
            "REPORT_GENERATION_ERROR",
            "Unable to generate the administrative PDF report.",
            500,
        )

    except Exception:
        return error_response(
            "REPORT_GENERATION_ERROR",
            "Unable to generate the administrative PDF report.",
            500,
        )


# =========================================================
# CSV REPORT
# =========================================================

@report_bp.get("/csv")
@jwt_required()
@roles_required("admin")
def generate_csv_report():
    """
    Generate and return an administrative CSV report.

    Optional query parameters:
        disease_class
        start_date
        end_date
    """

    filters = _get_report_filters()

    try:
        csv_file = ReportService.generate_csv(
            disease_class=filters["disease_class"],
            start_date=filters["start_date"],
            end_date=filters["end_date"],
        )

        return send_file(
            csv_file,
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name="maize_admin_report.csv",
        )

    except InvalidDateFilterError as exc:
        return error_response(
            "INVALID_DATE_FILTER",
            str(exc),
            400,
        )

    except ReportServiceError:
        return error_response(
            "REPORT_GENERATION_ERROR",
            "Unable to generate the administrative CSV report.",
            500,
        )

    except Exception:
        return error_response(
            "REPORT_GENERATION_ERROR",
            "Unable to generate the administrative CSV report.",
            500,
        )
