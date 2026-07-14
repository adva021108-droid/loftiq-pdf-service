"""PDF report generation for the Loftiq PDF service.

Exposes ``generate_report(data)`` which accepts a project data dict and
returns the rendered report as PDF bytes using ReportLab.
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

BRAND_COLOR = colors.HexColor("#1f3a5f")
ACCENT_COLOR = colors.HexColor("#4a90d9")
LIGHT_GREY = colors.HexColor("#f2f4f7")


def _styles():
    """Build the paragraph styles used throughout the report."""
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=24,
            leading=28,
            textColor=BRAND_COLOR,
            alignment=TA_LEFT,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#667085"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=BRAND_COLOR,
            spaceBefore=14,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["Normal"],
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#101828"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["Normal"],
            fontSize=10.5,
            leading=15,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Footer",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#98a2b3"),
            alignment=TA_CENTER,
        )
    )
    return styles


def _as_text(value):
    """Render an arbitrary value into a human readable string."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple)):
        return ", ".join(_as_text(v) for v in value) if value else "-"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_as_text(v)}" for k, v in value.items()) if value else "-"
    return str(value)


def _key_value_table(items, styles):
    """Build a two-column key/value table from an iterable of (label, value)."""
    rows = []
    for label, value in items:
        rows.append(
            [
                Paragraph(f"<b>{_as_text(label)}</b>", styles["Body"]),
                Paragraph(_as_text(value), styles["Body"]),
            ]
        )

    table = Table(rows, colWidths=[55 * mm, 110 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e4e7ec")),
            ]
        )
    )
    return table


# Fields that get their own dedicated rendering; everything else falls into
# a generic "Additional details" section so no supplied data is dropped.
_RESERVED_KEYS = {
    "title",
    "name",
    "project_name",
    "client",
    "client_name",
    "description",
    "summary",
    "status",
    "owner",
    "start_date",
    "end_date",
    "due_date",
    "budget",
    "items",
    "line_items",
    "tasks",
}


def generate_report(data):
    """Generate a PDF report from a project ``data`` dict.

    Args:
        data: A dict describing a project. All keys are optional; the
            renderer degrades gracefully when fields are missing.

    Returns:
        bytes: The rendered PDF document.
    """
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise TypeError("generate_report expects a dict of project data")

    styles = _styles()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=str(data.get("title") or data.get("project_name") or "Project Report"),
        author="Loftiq PDF Service",
    )

    story = []

    # --- Header -----------------------------------------------------------
    title = data.get("title") or data.get("project_name") or data.get("name") or "Project Report"
    story.append(Paragraph(_as_text(title), styles["ReportTitle"]))

    client = data.get("client") or data.get("client_name")
    subtitle_bits = []
    if client:
        subtitle_bits.append(f"Prepared for {_as_text(client)}")
    subtitle_bits.append("Generated " + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    story.append(Paragraph(" &nbsp;•&nbsp; ".join(subtitle_bits), styles["ReportSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT_COLOR, spaceAfter=10))

    # --- Overview ---------------------------------------------------------
    overview_fields = [
        ("Status", data.get("status")),
        ("Owner", data.get("owner")),
        ("Start date", data.get("start_date")),
        ("End date", data.get("end_date") or data.get("due_date")),
        ("Budget", data.get("budget")),
    ]
    overview_fields = [(k, v) for k, v in overview_fields if v is not None]
    if overview_fields:
        story.append(Paragraph("Overview", styles["SectionHeading"]))
        story.append(_key_value_table(overview_fields, styles))

    # --- Description ------------------------------------------------------
    description = data.get("description") or data.get("summary")
    if description:
        story.append(Paragraph("Description", styles["SectionHeading"]))
        story.append(Paragraph(_as_text(description), styles["Body"]))

    # --- Line items / tasks ----------------------------------------------
    items = data.get("items") or data.get("line_items") or data.get("tasks")
    if isinstance(items, (list, tuple)) and items:
        story.append(Paragraph("Items", styles["SectionHeading"]))
        story.append(_items_table(items, styles))

    # --- Additional details ----------------------------------------------
    extras = [
        (key, value)
        for key, value in data.items()
        if key not in _RESERVED_KEYS
    ]
    if extras:
        story.append(Paragraph("Additional details", styles["SectionHeading"]))
        story.append(_key_value_table(extras, styles))

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e7ec"), spaceAfter=6))
    story.append(Paragraph("Loftiq PDF Service", styles["Footer"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _items_table(items, styles):
    """Render a list of items into a table.

    Handles both a list of dicts (columns derived from the union of keys)
    and a list of scalars/strings (single column).
    """
    dict_items = [i for i in items if isinstance(i, dict)]

    if dict_items:
        # Preserve first-seen key order across all rows.
        columns = []
        for item in dict_items:
            for key in item.keys():
                if key not in columns:
                    columns.append(key)

        header = [Paragraph(f"<b>{_as_text(c)}</b>", styles["TableHeader"]) for c in columns]
        rows = [header]
        for item in dict_items:
            rows.append(
                [Paragraph(_as_text(item.get(c)), styles["Body"]) for c in columns]
            )
    else:
        rows = [[Paragraph("<b>Item</b>", styles["TableHeader"])]]
        for item in items:
            rows.append([Paragraph(_as_text(item), styles["Body"])])

    table = Table(rows, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e4e7ec")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e4e7ec")),
            ]
        )
    )
    return table
