from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from io import BytesIO


def generate_receipt_pdf(date, activities):

    # ---------- DYNAMIC RECEIPT HEIGHT (REAL CALCULATION) ----------
    header_space = 95      # title + date + quote + heart
    row_space = 20         # per activity row
    footer_space = 70      # total + thank you

    dynamic_height = header_space + footer_space + (len(activities) * row_space)

    # safety minimum
    if dynamic_height < 220:
        dynamic_height = 220

    # convert to mm (IMPORTANT!)
    dynamic_height = dynamic_height * mm

    # ---------- DOCUMENT ----------
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(80 * mm, dynamic_height),
        rightMargin=10,
        leftMargin=10,
        topMargin=12,
        bottomMargin=12
    )

    elements = []

    # ---------- STYLES ----------
    title_style = ParagraphStyle(
        name="title",
        alignment=TA_CENTER,
        fontName="DejaVu",
        fontSize=18,
        leading=22,
        spaceAfter=10
    )

    center = ParagraphStyle(
        name="center",
        alignment=TA_CENTER,
        fontName="DejaVu",
        fontSize=10,
        leading=14
    )

    left = ParagraphStyle(
        name="left",
        fontName="DejaVu",
        fontSize=10
    )

    right = ParagraphStyle(
        name="right",
        alignment=TA_RIGHT,
        fontName="DejaVu",
        fontSize=10
    )

    # ---------- HEADER ----------
    elements.append(Paragraph("<b>LIFE<br/>RECEIPT</b>", title_style))
    elements.append(Paragraph(date, center))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Keep collecting your life moments ♥", center))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("-------------------------------------------------", center))
    elements.append(Spacer(1, 10))

    # ---------- ACTIVITIES ----------
    total_minutes = 0
    rows = []

    for act in activities:
        mins = int(act["duration"])
        total_minutes += mins
        h = mins // 60
        m = mins % 60

        rows.append([
            Paragraph(act["activity_name"], left),
            Paragraph(f"{h}h {m}m", right)
        ])

    if rows:
        table = Table(rows, colWidths=[45 * mm, 20 * mm])

        table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))

        elements.append(table)

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("-------------------------------------------------", center))
    elements.append(Spacer(1, 6))

    # ---------- TOTAL ----------
    th = total_minutes // 60
    tm = total_minutes % 60

    total_table = Table(
        [[Paragraph("<b>TOTAL</b>", left),
          Paragraph(f"<b>{th}h {tm}m</b>", right)]],
        colWidths=[45 * mm, 20 * mm]
    )

    #total_table.setStyle(TableStyle([
    #   ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
    #    ("TOPPADDING", (0, 0), (-1, 0), 8),
    #]))

    elements.append(total_table)
    elements.append(Paragraph("-------------------------------------------------", center))
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("❤", center))
    elements.append(Paragraph("Thank you for showing up today!", center))

    # ---------- BUILD ----------
    doc.build(elements)

    pdf = buffer.getvalue()
    return pdf