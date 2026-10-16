
"""
=========================================================
Report Service
=========================================================

Generates administrative reports for the
AI-Based Maize Disease Detection System.

Responsibilities:
    - Reuse AdminService statistics.
    - Prepare report data.
    - Generate PDF reports.
    - Generate CSV reports.

Important:
    This service does NOT duplicate database/statistics
    queries already implemented in AdminService.
=========================================================
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.services.admin_service import (
    AdminService,
    InvalidDateFilterError,
)


class ReportServiceError(Exception):
    """Base exception for report-generation errors."""


class ReportService:
    """
    Service responsible for generating administrator reports.

    Statistics are obtained from AdminService so that report
    generation does not introduce duplicate business logic.
    """

    REPORT_TITLE = "AI-Based Maize Disease Detection System"
    REPORT_SUBTITLE = "Administrative Report"

    # -----------------------------------------------------
    # REPORT DATA
    # -----------------------------------------------------

    @classmethod
    def get_report_data(
        cls,
        disease_class: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Build the complete report dataset.

        All statistical calculations are delegated to
        AdminService.
        """

        try:
            dashboard = AdminService.get_dashboard_statistics()

            regional_statistics = AdminService.get_regional_statistics(
                disease_class=disease_class,
                start_date=start_date,
                end_date=end_date,
            )

            geo_disease_cases = AdminService.get_geo_disease_cases(
                disease_class=disease_class,
                start_date=start_date,
                end_date=end_date,
            )

        except InvalidDateFilterError:
            raise

        except Exception as exc:
            raise ReportServiceError(
                f"Failed to collect report data: {exc}"
            ) from exc

        diagnoses = dashboard.get("diagnoses", {})
        users = dashboard.get("users", {})
        advisories = dashboard.get("advisories", {})
        extension_comments = dashboard.get(
            "extension_comments",
            {},
        )

        # The dashboard contains overall statistics.
        # When filters are supplied, the regional/geo methods
        # provide the filtered diagnosis statistics.
        #
        # Therefore, calculate filtered diagnosis summary
        # from the regional statistics when filters exist.
        has_filters = any(
            value is not None and str(value).strip()
            for value in (
                disease_class,
                start_date,
                end_date,
            )
        )

        if has_filters:
            diagnosis_summary = {
                "total": regional_statistics.get("summary", {}).get(
                    "total_diagnoses",
                    0,
                ),
                "healthy": regional_statistics.get("summary", {}).get(
                    "healthy_cases",
                    0,
                ),
                "diseased": regional_statistics.get("summary", {}).get(
                    "diseased_cases",
                    0,
                ),
                "by_disease": regional_statistics.get(
                    "by_disease",
                    [],
                ),
            }
        else:
            diagnosis_summary = diagnoses

        generated_at = datetime.now(timezone.utc).isoformat()

        return {
            "report": {
                "title": cls.REPORT_TITLE,
                "subtitle": cls.REPORT_SUBTITLE,
                "generated_at": generated_at,
                "filters": {
                    "disease_class": disease_class,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            },
            "users": users,
            "diagnoses": diagnosis_summary,
            "advisories": advisories,
            "extension_comments": extension_comments,
            "regional_statistics": regional_statistics,
            "geo_disease_cases": geo_disease_cases,
            "recent_diagnoses": (
                dashboard.get("recent_diagnoses", [])
                if not has_filters
                else []
            ),
            "recent_users": dashboard.get(
                "recent_users",
                [],
            ),
        }

    # -----------------------------------------------------
    # HELPERS
    # -----------------------------------------------------

    @staticmethod
    def _safe_value(value: Any) -> str:
        """Convert a value safely to displayable text."""

        if value is None:
            return ""

        if isinstance(value, bool):
            return "Yes" if value else "No"

        return str(value)

    @classmethod
    def _format_date(cls, value: Any) -> str:
        """Format ISO datetime/date values for PDF output."""

        if value is None:
            return ""

        text = str(value)

        if "T" in text:
            text = text.split("T", 1)[0]

        return text

    @classmethod
    def _add_section_title(
        cls,
        story: list[Any],
        title: str,
        styles: Any,
    ) -> None:
        """Add a consistent PDF section heading."""

        story.append(
            Paragraph(
                title,
                styles["Heading2"],
            )
        )
        story.append(Spacer(1, 4 * mm))

    @classmethod
    def _build_table(
        cls,
        headers: list[str],
        rows: list[list[Any]],
        column_widths: list[float] | None = None,
    ) -> Table:
        """
        Build a consistently styled ReportLab table.
        """

        formatted_rows = [
            [
                cls._safe_value(value)
                for value in row
            ]
            for row in rows
        ]

        table_data = [
            headers,
            *formatted_rows,
        ]

        table = Table(
            table_data,
            colWidths=column_widths,
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#2F5597"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, -1),
                        "Helvetica",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 0),
                        6,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, 0),
                        6,
                    ),
                ]
            )
        )

        return table

    # -----------------------------------------------------
    # PDF GENERATION
    # -----------------------------------------------------

    @classmethod
    def generate_pdf(
        cls,
        disease_class: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> BytesIO:
        """
        Generate an administrative PDF report.

        Returns:
            BytesIO containing the generated PDF.
        """

        report_data = cls.get_report_data(
            disease_class=disease_class,
            start_date=start_date,
            end_date=end_date,
        )

        output = BytesIO()

        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title=cls.REPORT_TITLE,
            author="AI-Based Maize Disease Detection System",
        )

        base_styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=base_styles["Title"],
            alignment=TA_CENTER,
            fontSize=18,
            leading=22,
            spaceAfter=5 * mm,
        )

        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=base_styles["Normal"],
            alignment=TA_CENTER,
            fontSize=11,
            leading=14,
            spaceAfter=8 * mm,
        )

        story: list[Any] = []

        report_info = report_data["report"]

        story.append(
            Paragraph(
                report_info["title"],
                title_style,
            )
        )

        story.append(
            Paragraph(
                report_info["subtitle"],
                subtitle_style,
            )
        )

        story.append(
            Paragraph(
                "Generated: "
                + cls._safe_value(
                    report_info["generated_at"]
                ),
                base_styles["Normal"],
            )
        )

        filters = report_info["filters"]

        filter_rows = []

        if filters.get("disease_class"):
            filter_rows.append(
                [
                    "Disease",
                    filters["disease_class"],
                ]
            )

        if filters.get("start_date"):
            filter_rows.append(
                [
                    "Start Date",
                    filters["start_date"],
                ]
            )

        if filters.get("end_date"):
            filter_rows.append(
                [
                    "End Date",
                    filters["end_date"],
                ]
            )

        if filter_rows:
            story.append(Spacer(1, 4 * mm))
            story.append(
                cls._build_table(
                    ["Filter", "Value"],
                    filter_rows,
                    [45 * mm, 100 * mm],
                )
            )

        story.append(Spacer(1, 8 * mm))

        # -------------------------------------------------
        # USER STATISTICS
        # -------------------------------------------------

        cls._add_section_title(
            story,
            "1. User Statistics",
            base_styles,
        )

        users = report_data["users"]

        user_summary_rows = [
            [
                "Total Users",
                users.get("total", 0),
            ],
            [
                "Farmers",
                users.get("farmers", 0),
            ],
            [
                "Extension Agents",
                users.get("extension_agents", 0),
            ],
            [
                "Administrators",
                users.get("admins", 0),
            ],
            [
                "Active Users",
                users.get("active", 0),
            ],
            [
                "Inactive Users",
                users.get("inactive", 0),
            ],
        ]

        story.append(
            cls._build_table(
                ["Metric", "Value"],
                user_summary_rows,
                [100 * mm, 45 * mm],
            )
        )

        story.append(Spacer(1, 8 * mm))

        # -------------------------------------------------
        # DIAGNOSIS STATISTICS
        # -------------------------------------------------

        cls._add_section_title(
            story,
            "2. Diagnosis Statistics",
            base_styles,
        )

        diagnoses = report_data["diagnoses"]

        diagnosis_summary_rows = [
            [
                "Total Diagnoses",
                diagnoses.get("total", 0),
            ],
            [
                "Healthy Cases",
                diagnoses.get("healthy", 0),
            ],
            [
                "Diseased Cases",
                diagnoses.get("diseased", 0),
            ],
        ]

        story.append(
            cls._build_table(
                ["Metric", "Value"],
                diagnosis_summary_rows,
                [100 * mm, 45 * mm],
            )
        )

        story.append(Spacer(1, 4 * mm))

        disease_rows = diagnoses.get(
            "by_disease",
            [],
        )

        if disease_rows:
            formatted_disease_rows = []

            for item in disease_rows:
                if isinstance(item, dict):
                    formatted_disease_rows.append(
                        [
                            item.get(
                                "disease_class",
                                "",
                            ),
                            item.get(
                                "count",
                                0,
                            ),
                        ]
                    )

            if formatted_disease_rows:
                story.append(
                    cls._build_table(
                        ["Disease Class", "Cases"],
                        formatted_disease_rows,
                        [100 * mm, 45 * mm],
                    )
                )

        story.append(Spacer(1, 8 * mm))

        # -------------------------------------------------
        # ADVISORY / COMMENTS
        # -------------------------------------------------

        cls._add_section_title(
            story,
            "3. Advisory and Communication Statistics",
            base_styles,
        )

        advisories = report_data["advisories"]
        comments = report_data["extension_comments"]

        communication_rows = [
            [
                "Advisories",
                advisories.get("total", 0),
            ],
            [
                "Extension Comments",
                comments.get("total", 0),
            ],
        ]

        story.append(
            cls._build_table(
                ["Metric", "Value"],
                communication_rows,
                [100 * mm, 45 * mm],
            )
        )

        story.append(Spacer(1, 8 * mm))

        # -------------------------------------------------
        # REGIONAL STATISTICS
        # -------------------------------------------------

        cls._add_section_title(
            story,
            "4. Regional Statistics",
            base_styles,
        )

        regional = report_data["regional_statistics"]

        regional_summary = regional.get(
            "summary",
            {},
        )

        regional_summary_rows = [
            [
                "Total Diagnoses",
                regional_summary.get(
                    "total_diagnoses",
                    0,
                ),
            ],
            [
                "Healthy Cases",
                regional_summary.get(
                    "healthy_cases",
                    0,
                ),
            ],
            [
                "Diseased Cases",
                regional_summary.get(
                    "diseased_cases",
                    0,
                ),
            ],
        ]

        story.append(
            cls._build_table(
                ["Metric", "Value"],
                regional_summary_rows,
                [100 * mm, 45 * mm],
            )
        )

        story.append(Spacer(1, 4 * mm))

        # By region
        by_region = regional.get(
            "by_region",
            [],
        )

        if by_region:
            rows = []

            for item in by_region:
                rows.append(
                    [
                        item.get("region", ""),
                        item.get("count", 0),
                    ]
                )

            story.append(
                Paragraph(
                    "Cases by Region",
                    base_styles["Heading3"],
                )
            )

            story.append(
                cls._build_table(
                    ["Region", "Cases"],
                    rows,
                    [100 * mm, 45 * mm],
                )
            )

            story.append(Spacer(1, 4 * mm))

        # By woreda
        by_woreda = regional.get(
            "by_woreda",
            [],
        )

        if by_woreda:
            rows = []

            for item in by_woreda:
                rows.append(
                    [
                        item.get("woreda", ""),
                        item.get("count", 0),
                    ]
                )

            story.append(
                Paragraph(
                    "Cases by Woreda",
                    base_styles["Heading3"],
                )
            )

            story.append(
                cls._build_table(
                    ["Woreda", "Cases"],
                    rows,
                    [100 * mm, 45 * mm],
                )
            )

            story.append(Spacer(1, 4 * mm))

        # By kebele
        by_kebele = regional.get(
            "by_kebele",
            [],
        )

        if by_kebele:
            rows = []

            for item in by_kebele:
                rows.append(
                    [
                        item.get("region", ""),
                        item.get("woreda", ""),
                        item.get("kebele", ""),
                        item.get("count", 0),
                    ]
                )

            story.append(
                Paragraph(
                    "Cases by Kebele",
                    base_styles["Heading3"],
                )
            )

            story.append(
                cls._build_table(
                    [
                        "Region",
                        "Woreda",
                        "Kebele",
                        "Cases",
                    ],
                    rows,
                    [
                        38 * mm,
                        38 * mm,
                        35 * mm,
                        34 * mm,
                    ],
                )
            )

        story.append(Spacer(1, 8 * mm))

        # -------------------------------------------------
        # TRENDS
        # -------------------------------------------------

        trends = regional.get(
            "trends",
            [],
        )

        if trends:
            cls._add_section_title(
                story,
                "5. Diagnosis Trends",
                base_styles,
            )

            trend_rows = []

            for item in trends:
                trend_rows.append(
                    [
                        item.get("date", ""),
                        item.get("count", 0),
                    ]
                )

            story.append(
                cls._build_table(
                    ["Date", "Diagnoses"],
                    trend_rows,
                    [100 * mm, 45 * mm],
                )
            )

            story.append(Spacer(1, 8 * mm))

        # -------------------------------------------------
        # GEO-DISEASE CASES
        # -------------------------------------------------

        geo = report_data["geo_disease_cases"]

        if isinstance(geo, dict):
            geo_cases = geo.get(
                "cases",
                [],
            )
            mapped_total = geo.get(
                "total_mapped_cases",
                len(geo_cases),
            )
        else:
            geo_cases = geo if isinstance(geo, list) else []
            mapped_total = len(geo_cases)

        cls._add_section_title(
            story,
            "6. Geographic Disease Cases",
            base_styles,
        )

        story.append(
            Paragraph(
                f"Mapped cases: {mapped_total}",
                base_styles["Normal"],
            )
        )

        story.append(Spacer(1, 4 * mm))

        if geo_cases:
            geo_rows = []

            for item in geo_cases:
                geo_rows.append(
                    [
                        item.get("diagnosis_id", ""),
                        item.get("disease_class", ""),
                        item.get("region", ""),
                        item.get("woreda", ""),
                        item.get("kebele", ""),
                        item.get("latitude", ""),
                        item.get("longitude", ""),
                    ]
                )

            story.append(
                cls._build_table(
                    [
                        "ID",
                        "Disease",
                        "Region",
                        "Woreda",
                        "Kebele",
                        "Latitude",
                        "Longitude",
                    ],
                    geo_rows,
                    [
                        12 * mm,
                        28 * mm,
                        27 * mm,
                        27 * mm,
                        23 * mm,
                        25 * mm,
                        25 * mm,
                    ],
                )
            )
        else:
            story.append(
                Paragraph(
                    "No diagnosis cases with valid geographic "
                    "coordinates are currently available.",
                    base_styles["Normal"],
                )
            )

        story.append(Spacer(1, 8 * mm))

        # -------------------------------------------------
        # RECENT DIAGNOSES
        # -------------------------------------------------

        recent_diagnoses = report_data.get(
            "recent_diagnoses",
            [],
        )

        if recent_diagnoses:
            cls._add_section_title(
                story,
                "7. Recent Diagnoses",
                base_styles,
            )

            recent_rows = []

            for item in recent_diagnoses:
                recent_rows.append(
                    [
                        item.get("id", ""),
                        item.get("disease_class", ""),
                        item.get("confidence", ""),
                        cls._format_date(
                            item.get(
                                "created_at",
                                "",
                            )
                        ),
                    ]
                )

            story.append(
                cls._build_table(
                    [
                        "ID",
                        "Disease",
                        "Confidence",
                        "Date",
                    ],
                    recent_rows,
                    [
                        18 * mm,
                        55 * mm,
                        35 * mm,
                        37 * mm,
                    ],
                )
            )

        # -------------------------------------------------
        # RECENT USERS
        # -------------------------------------------------

        recent_users = report_data.get(
            "recent_users",
            [],
        )

        if recent_users:
            story.append(Spacer(1, 8 * mm))

            cls._add_section_title(
                story,
                "8. Recent Users",
                base_styles,
            )

            recent_user_rows = []

            for item in recent_users:
                recent_user_rows.append(
                    [
                        item.get("id", ""),
                        item.get("full_name", ""),
                        item.get("role", ""),
                        item.get("phone_number", ""),
                        cls._format_date(
                            item.get(
                                "created_at",
                                "",
                            )
                        ),
                    ]
                )

            story.append(
                cls._build_table(
                    [
                        "ID",
                        "Name",
                        "Role",
                        "Phone",
                        "Created",
                    ],
                    recent_user_rows,
                    [
                        12 * mm,
                        42 * mm,
                        30 * mm,
                        38 * mm,
                        25 * mm,
                    ],
                )
            )

        # -------------------------------------------------
        # FOOTER
        # -------------------------------------------------

        story.append(Spacer(1, 10 * mm))

        story.append(
            Paragraph(
                "AI-Based Maize Disease Detection System — "
                "Administrative Report",
                ParagraphStyle(
                    "Footer",
                    parent=base_styles["Normal"],
                    alignment=TA_CENTER,
                    fontSize=8,
                ),
            )
        )

        document.build(story)

        output.seek(0)

        return output

    # -----------------------------------------------------
    # CSV GENERATION
    # -----------------------------------------------------

    @classmethod
    def generate_csv(
        cls,
        disease_class: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> BytesIO:
        """
        Generate a CSV administrative report.

        The CSV contains summary statistics followed by
        regional, disease, trend, and geographic records.
        """

        report_data = cls.get_report_data(
            disease_class=disease_class,
            start_date=start_date,
            end_date=end_date,
        )

        text_output = StringIO(
            newline="",
        )

        writer = csv.writer(text_output)

        # -------------------------------------------------
        # REPORT INFORMATION
        # -------------------------------------------------

        writer.writerow(
            [
                "AI-Based Maize Disease Detection System"
            ]
        )

        writer.writerow(
            [
                "Administrative Report"
            ]
        )

        writer.writerow(
            [
                "Generated At",
                report_data["report"]["generated_at"],
            ]
        )

        filters = report_data["report"]["filters"]

        writer.writerow(
            [
                "Disease Filter",
                filters.get(
                    "disease_class",
                    "",
                ),
            ]
        )

        writer.writerow(
            [
                "Start Date",
                filters.get(
                    "start_date",
                    "",
                ),
            ]
        )

        writer.writerow(
            [
                "End Date",
                filters.get(
                    "end_date",
                    "",
                ),
            ]
        )

        writer.writerow([])

        # -------------------------------------------------
        # USERS
        # -------------------------------------------------

        writer.writerow(
            ["USER STATISTICS"]
        )

        users = report_data["users"]

        writer.writerow(
            ["Metric", "Value"]
        )

        writer.writerow(
            [
                "Total Users",
                users.get("total", 0),
            ]
        )

        writer.writerow(
            [
                "Farmers",
                users.get("farmers", 0),
            ]
        )

        writer.writerow(
            [
                "Extension Agents",
                users.get(
                    "extension_agents",
                    0,
                ),
            ]
        )

        writer.writerow(
            [
                "Administrators",
                users.get("admins", 0),
            ]
        )

        writer.writerow(
            [
                "Active Users",
                users.get("active", 0),
            ]
        )

        writer.writerow(
            [
                "Inactive Users",
                users.get("inactive", 0),
            ]
        )

        writer.writerow([])

        # -------------------------------------------------
        # DIAGNOSES
        # -------------------------------------------------

        writer.writerow(
            ["DIAGNOSIS STATISTICS"]
        )

        diagnoses = report_data["diagnoses"]

        writer.writerow(
            ["Metric", "Value"]
        )

        writer.writerow(
            [
                "Total Diagnoses",
                diagnoses.get("total", 0),
            ]
        )

        writer.writerow(
            [
                "Healthy Cases",
                diagnoses.get("healthy", 0),
            ]
        )

        writer.writerow(
            [
                "Diseased Cases",
                diagnoses.get("diseased", 0),
            ]
        )

        writer.writerow([])

        writer.writerow(
            [
                "Disease Class",
                "Cases",
            ]
        )

        for item in diagnoses.get(
            "by_disease",
            [],
        ):
            if isinstance(item, dict):
                writer.writerow(
                    [
                        item.get(
                            "disease_class",
                            "",
                        ),
                        item.get(
                            "count",
                            0,
                        ),
                    ]
                )

        writer.writerow([])

        # -------------------------------------------------
        # COMMUNICATION
        # -------------------------------------------------

        writer.writerow(
            ["ADVISORY AND COMMUNICATION"]
        )

        writer.writerow(
            [
                "Advisories",
                report_data["advisories"].get(
                    "total",
                    0,
                ),
            ]
        )

        writer.writerow(
            [
                "Extension Comments",
                report_data[
                    "extension_comments"
                ].get(
                    "total",
                    0,
                ),
            ]
        )

        writer.writerow([])

        # -------------------------------------------------
        # REGIONAL STATISTICS
        # -------------------------------------------------

        regional = report_data[
            "regional_statistics"
        ]

        writer.writerow(
            ["REGIONAL SUMMARY"]
        )

        regional_summary = regional.get(
            "summary",
            {},
        )

        writer.writerow(
            [
                "Total Diagnoses",
                regional_summary.get(
                    "total_diagnoses",
                    0,
                ),
            ]
        )

        writer.writerow(
            [
                "Healthy Cases",
                regional_summary.get(
                    "healthy_cases",
                    0,
                ),
            ]
        )

        writer.writerow(
            [
                "Diseased Cases",
                regional_summary.get(
                    "diseased_cases",
                    0,
                ),
            ]
        )

        writer.writerow([])

        writer.writerow(
            ["CASES BY REGION"]
        )

        writer.writerow(
            [
                "Region",
                "Cases",
            ]
        )

        for item in regional.get(
            "by_region",
            [],
        ):
            writer.writerow(
                [
                    item.get(
                        "region",
                        "",
                    ),
                    item.get(
                        "count",
                        0,
                    ),
                ]
            )

        writer.writerow([])

        writer.writerow(
            ["CASES BY WOREDA"]
        )

        writer.writerow(
            [
                "Woreda",
                "Cases",
            ]
        )

        for item in regional.get(
            "by_woreda",
            [],
        ):
            writer.writerow(
                [
                    item.get(
                        "woreda",
                        "",
                    ),
                    item.get(
                        "count",
                        0,
                    ),
                ]
            )

        writer.writerow([])

        writer.writerow(
            ["CASES BY KEBELE"]
        )

        writer.writerow(
            [
                "Region",
                "Woreda",
                "Kebele",
                "Cases",
            ]
        )

        for item in regional.get(
            "by_kebele",
            [],
        ):
            writer.writerow(
                [
                    item.get(
                        "region",
                        "",
                    ),
                    item.get(
                        "woreda",
                        "",
                    ),
                    item.get(
                        "kebele",
                        "",
                    ),
                    item.get(
                        "count",
                        0,
                    ),
                ]
            )

        writer.writerow([])

        # -------------------------------------------------
        # TRENDS
        # -------------------------------------------------

        writer.writerow(
            ["DIAGNOSIS TRENDS"]
        )

        writer.writerow(
            [
                "Date",
                "Diagnoses",
            ]
        )

        for item in regional.get(
            "trends",
            [],
        ):
            writer.writerow(
                [
                    item.get(
                        "date",
                        "",
                    ),
                    item.get(
                        "count",
                        0,
                    ),
                ]
            )

        writer.writerow([])

        # -------------------------------------------------
        # GEO CASES
        # -------------------------------------------------

        writer.writerow(
            ["GEOGRAPHIC DISEASE CASES"]
        )

        writer.writerow(
            [
                "Diagnosis ID",
                "Disease",
                "Region",
                "Woreda",
                "Kebele",
                "Latitude",
                "Longitude",
            ]
        )

        geo = report_data[
            "geo_disease_cases"
        ]

        if isinstance(geo, dict):
            geo_cases = geo.get(
                "cases",
                [],
            )
        else:
            geo_cases = (
                geo
                if isinstance(geo, list)
                else []
            )

        for item in geo_cases:
            writer.writerow(
                [
                    item.get(
                        "diagnosis_id",
                        "",
                    ),
                    item.get(
                        "disease_class",
                        "",
                    ),
                    item.get(
                        "region",
                        "",
                    ),
                    item.get(
                        "woreda",
                        "",
                    ),
                    item.get(
                        "kebele",
                        "",
                    ),
                    item.get(
                        "latitude",
                        "",
                    ),
                    item.get(
                        "longitude",
                        "",
                    ),
                ]
            )

        # -------------------------------------------------
        # FINALIZE
        # -------------------------------------------------

        output = BytesIO(
            text_output.getvalue().encode(
                "utf-8-sig"
            )
        )

        output.seek(0)

        return output

