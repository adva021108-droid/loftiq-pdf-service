"""PDF report generation for the Loftiq PDF service."""

from io import BytesIO
from datetime import datetime
import urllib.request

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
    Image,
)

BRAND_COLOR = colors.HexColor("#1f3a5f")
ACCENT_COLOR = colors.HexColor("#4a90d9")
LIGHT_GREY = colors.HexColor("#f2f4f7")

CONTRACTOR_KEYS = {
    "contractor_name",
    "contractor_phone",
    "contractor_whatsapp",
    "contractor_email",
    "contractor_logo_url",
}

_RESERVED_KEYS = {
    "title", "name", "project_name", "client", "client_name",
    "description", "summary", "status", "owner", "start_date",
    "end_date", "due_date", "budget", "items", "line_items", "tasks",
    *CONTRACTOR_KEYS,
}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"],
        fontSize=24, leading=28, textColor=BRAND_COLOR,
        alignment=TA_LEFT, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle", parent=styles["Normal"],
        fontSize=11, leading=14, textColor=colors.HexColor("#667085"), spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"],
        fontSize=14, leading=18, textColor=BRAND_COLOR, spaceBefore=14, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Body", parent=styles["Normal"],
        fontSize=10.5, leading=15, textColor=colors.HexColor("#101828"), spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader", parent=styles["Normal"],
        fontSize=10.5, leading=15, textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="Footer", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=colors.HexColor("#98a2b3"), alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="ContractorName", parent=styles["Normal"],
        fontSize=13, leading=16, textColor=BRAND_COLOR, alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name="ContractorDetail", parent=styles["Normal"],
        fontSize=9.5, leading=13, textColor=colors.HexColor("#667085"), alignment=TA_RIGHT,
    ))
    return styles


def _as_text(value):
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
    rows = []
    for label, value in items:
        rows.append([
            Paragraph(f"<b>{_as_text(label)}</b>", styles["Body"]),
            Paragraph(_as_text(value), styles["Body"]),
        ])
    table = Table(rows, colWidths=[55 * mm, 110 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e4e7ec")),
    ]))
    return table


def _fetch_logo(url, max_height=18 * mm):
    """Download logo from URL and return a ReportLab Image, or None on failure."""
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read()
        buf = BytesIO(data)
        img = Image(buf)
        # Scale to max height preserving aspect ratio
        w, h = img.drawWidth, img.drawHeight
        scale = max_height / h
        img.drawWidth = w * scale
        img.drawHeight = max_height
        return img
    except Exception:
        return None


def _contractor_header(data, styles, page_width):
    """Build a header row: logo on left, contractor name+phone on right."""
    logo_url = data.get("contractor_logo_url")
    contractor_name = data.get("contractor_name")
    contractor_phone = data.get("contractor_phone") or data.get("contractor_whatsapp")
    contractor_email = data.get("contractor_email")

    if not contractor_name and not logo_url:
        return None

    # Left cell: logo or empty
    logo_img = _fetch_logo(logo_url)
    left_cell = logo_img if logo_img else Paragraph("", styles["Body"])

    # Right cell: name + contact details
    right_parts = []
    if contractor_name:
        right_parts.append(Paragraph(f"<b>{contractor_name}</b>", styles["ContractorName"]))
    if contractor_phone:
        right_parts.append(Paragraph(contractor_phone, styles["ContractorDetail"]))
    if contractor_email:
        right_parts.append(Paragraph(contractor_email, styles["ContractorDetail"]))

    right_cell = right_parts if right_parts else Paragraph("", styles["Body"])

    col_w = page_width - 40 * mm  # total usable width
    table = Table(
        [[left_cell, right_cell]],
        colWidths=[col_w * 0.35, col_w * 0.65],
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def generate_report(data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise TypeError("generate_report expects a dict of project data")

    styles = _styles()
    buffer = BytesIO()
    page_w, page_h = A4

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

    # --- Contractor header (logo + name/phone) ---
    contractor_header = _contractor_header(data, styles, page_w)
    if contractor_header:
        story.append(contractor_header)
        story.append(Spacer(1, 6))

    # --- Report title ---
    title = data.get("title") or data.get("project_name") or data.get("name") or "Project Report"
    story.append(Paragraph(_as_text(title), styles["ReportTitle"]))

    client = data.get("client") or data.get("client_name")
    subtitle_bits = []
    if client:
        subtitle_bits.append(f"Prepared for {_as_text(client)}")
    subtitle_bits.append("Generated " + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    story.append(Paragraph(" &nbsp;•&nbsp; ".join(subtitle_bits), styles["ReportSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT_COLOR, spaceAfter=10))

    # --- Overview ---
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

    # --- Description ---
    description = data.get("description") or data.get("summary")
    if description:
        story.append(Paragraph("Description", styles["SectionHeading"]))
        story.append(Paragraph(_as_text(description), styles["Body"]))

    # --- Line items ---
    items = data.get("items") or data.get("line_items") or data.get("tasks")
    if isinstance(items, (list, tuple)) and items:
        story.append(Paragraph("Items", styles["SectionHeading"]))
        story.append(_items_table(items, styles))

    # --- Additional details (non-reserved keys) ---
    extras = [(k, v) for k, v in data.items() if k not in _RESERVED_KEYS]
    if extras:
        story.append(Paragraph("Additional details", styles["SectionHeading"]))
        story.append(_key_value_table(extras, styles))

    # --- Footer ---
    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e7ec"), spaceAfter=6))

    footer_parts = []
    contractor_name = data.get("contractor_name")
    if contractor_name:
        footer_parts.append(contractor_name)
    footer_parts.append("Powered by Loftiq")
    story.append(Paragraph(" • ".join(footer_parts), styles["Footer"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _items_table(items, styles):
    dict_items = [i for i in items if isinstance(i, dict)]
    if dict_items:
        columns = []
        for item in dict_items:
            for key in item.keys():
                if key not in columns:
                    columns.append(key)
        header = [Paragraph(f"<b>{_as_text(c)}</b>", styles["TableHeader"]) for c in columns]
        rows = [header]
        for item in dict_items:
            rows.append([Paragraph(_as_text(item.get(c)), styles["Body"]) for c in columns])
    else:
        rows = [[Paragraph("<b>Item</b>", styles["TableHeader"])]]
        for item in items:
            rows.append([Paragraph(_as_text(item), styles["Body"])])

    table = Table(rows, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
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
    ]))
    return table
