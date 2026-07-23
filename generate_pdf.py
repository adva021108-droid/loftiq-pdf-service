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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image,
)

BRAND_COLOR = colors.HexColor("#1f3a5f")
ACCENT_COLOR = colors.HexColor("#4a90d9")
LIGHT_GREY = colors.HexColor("#f2f4f7")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"],
        fontSize=22, leading=26, textColor=BRAND_COLOR, alignment=TA_LEFT, spaceAfter=4))
    styles.add(ParagraphStyle(name="ReportSubtitle", parent=styles["Normal"],
        fontSize=10, leading=13, textColor=colors.HexColor("#667085"), spaceAfter=10))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"],
        fontSize=13, leading=17, textColor=BRAND_COLOR, spaceBefore=12, spaceAfter=5))
    styles.add(ParagraphStyle(name="Body", parent=styles["Normal"],
        fontSize=10, leading=14, textColor=colors.HexColor("#101828"), spaceAfter=4))
    styles.add(ParagraphStyle(name="TableHeader", parent=styles["Normal"],
        fontSize=10, leading=14, textColor=colors.white))
    styles.add(ParagraphStyle(name="Footer", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=colors.HexColor("#98a2b3"), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="ContractorName", parent=styles["Normal"],
        fontSize=13, leading=16, textColor=BRAND_COLOR, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="ContractorDetail", parent=styles["Normal"],
        fontSize=9, leading=12, textColor=colors.HexColor("#667085"), alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="Link", parent=styles["Normal"],
        fontSize=9, leading=12, textColor=ACCENT_COLOR, spaceAfter=4))
    return styles


def _fetch_logo(url, max_height=16 * mm):
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read()
        buf = BytesIO(data)
        img = Image(buf)
        w, h = img.drawWidth, img.drawHeight
        scale = max_height / h
        img.drawWidth = w * scale
        img.drawHeight = max_height
        return img
    except Exception:
        return None


def _contractor_header(data, styles, page_width):
    logo_url = data.get("contractor_logo_url")
    contractor_name = data.get("contractor_name")
    contractor_phone = data.get("contractor_phone") or data.get("contractor_whatsapp")
    contractor_email = data.get("contractor_email")

    logo_img = _fetch_logo(logo_url)
    left_cell = logo_img if logo_img else Paragraph("", styles["Body"])

    right_parts = []
    if contractor_name:
        right_parts.append(Paragraph(f"<b>{contractor_name}</b>", styles["ContractorName"]))
    if contractor_phone:
        right_parts.append(Paragraph(contractor_phone, styles["ContractorDetail"]))
    if contractor_email:
        right_parts.append(Paragraph(contractor_email, styles["ContractorDetail"]))

    right_cell = right_parts if right_parts else Paragraph("", styles["Body"])
    col_w = page_width - 40 * mm
    table = Table([[left_cell, right_cell]],
        colWidths=[col_w * 0.35, col_w * 0.65], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _scenarios_table(scenarios, styles):
    header = [
        Paragraph("<b>Scenario</b>", styles["TableHeader"]),
        Paragraph("<b>Usable Area (m²)</b>", styles["TableHeader"]),
        Paragraph("<b>Shell Cost (inc. VAT)</b>", styles["TableHeader"]),
        Paragraph("<b>Turnkey Cost (inc. VAT)</b>", styles["TableHeader"]),
    ]
    rows = [header]
    for s in scenarios:
        name = s.get("name", "-")
        area = s.get("usable_area_m2")
        shell = s.get("shell_total_inc_vat")
        turnkey = s.get("turnkey_total_inc_vat")
        rows.append([
            Paragraph(str(name), styles["Body"]),
            Paragraph(f"{area:.1f}" if area is not None else "-", styles["Body"]),
            Paragraph(f"£{shell:,.0f}" if shell is not None else "-", styles["Body"]),
            Paragraph(f"£{turnkey:,.0f}" if turnkey is not None else "-", styles["Body"]),
        ])
    col_w = [60*mm, 35*mm, 45*mm, 45*mm]
    table = Table(rows, colWidths=col_w, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e4e7ec")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e4e7ec")),
    ]))
    return table


def generate_report(data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise TypeError("generate_report expects a dict")

    styles = _styles()
    buffer = BytesIO()
    page_w, page_h = A4

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=18*mm,
        title="Loft Conversion Report",
        author="Loftiq",
    )

    story = []

    # Contractor header
    story.append(_contractor_header(data, styles, page_w))
    story.append(Spacer(1, 6))

    # Title
    address = data.get("property_address") or "Loft Conversion Report"
    story.append(Paragraph(address, styles["ReportTitle"]))

    # Subtitle
    client = data.get("client_name") or data.get("client")
    subtitle_bits = []
    if client:
        subtitle_bits.append(f"Prepared for {client}")
    subtitle_bits.append("Generated " + datetime.utcnow().strftime("%d %b %Y"))
    story.append(Paragraph(" &nbsp;•&nbsp; ".join(subtitle_bits), styles["ReportSubtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT_COLOR, spaceAfter=10))

    # Client details
    client_rows = []
    if data.get("client_name"):
        client_rows.append(("Client", data["client_name"]))
    if data.get("client_email"):
        client_rows.append(("Email", data["client_email"]))
    if data.get("client_whatsapp"):
        client_rows.append(("WhatsApp", data["client_whatsapp"]))
    if client_rows:
        story.append(Paragraph("Client Details", styles["SectionHeading"]))
        kv_rows = []
        for label, value in client_rows:
            kv_rows.append([
                Paragraph(f"<b>{label}</b>", styles["Body"]),
                Paragraph(str(value), styles["Body"]),
            ])
        t = Table(kv_rows, colWidths=[50*mm, 120*mm], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e4e7ec")),
        ]))
        story.append(t)

    # Scenarios table
    scenarios = data.get("scenarios")
    if isinstance(scenarios, list) and scenarios:
        story.append(Paragraph("Loft Conversion Scenarios", styles["SectionHeading"]))
        story.append(_scenarios_table(scenarios, styles))

    # Report link
    report_link = data.get("report_link")
    if report_link:
        story.append(Spacer(1, 10))
        story.append(Paragraph("View full interactive report:", styles["Body"]))
        story.append(Paragraph(f'<a href="{report_link}" color="#4a90d9">{report_link}</a>', styles["Link"]))

    # Footer
    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e7ec"), spaceAfter=6))
    footer_parts = []
    if data.get("contractor_name"):
        footer_parts.append(data["contractor_name"])
    footer_parts.append("Powered by Loftiq")
    story.append(Paragraph(" • ".join(footer_parts), styles["Footer"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
