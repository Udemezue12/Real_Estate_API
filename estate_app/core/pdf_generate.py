from pathlib import Path

from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE_PATH = Path("media/receipts")
BASE_PATH.mkdir(parents=True, exist_ok=True)


class ReceiptGenerator:
    @staticmethod
    def generate_pdf(receipt):
        file_path = BASE_PATH / f"{receipt.reference_number}.pdf"

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )

        styles = getSampleStyleSheet()

        styles.add(
            ParagraphStyle(
                name="TitleStyle",
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=12,
                textColor=colors.HexColor("#1F2937"),
            )
        )

        styles.add(
            ParagraphStyle(
                name="SectionHeader",
                fontSize=12,
                spaceBefore=14,
                spaceAfter=6,
                textColor=colors.HexColor("#111827"),
                fontName="Helvetica-Bold",
            )
        )

        styles.add(
            ParagraphStyle(
                name="Meta",
                fontSize=9,
                alignment=TA_RIGHT,
                textColor=colors.grey,
            )
        )

        elements = []

        elements.append(Paragraph("RENT PAYMENT RECEIPT", styles["TitleStyle"]))
        elements.append(
            Paragraph(
                f"Reference Number: <b>{receipt.reference_number}</b>",
                styles["Meta"],
            )
        )
       
        barcode_value = receipt.barcode_reference

        barcode = code128.Code128(
            barcode_value,
            barHeight=20 * mm,
            barWidth=0.6,
        )

        elements.append(Spacer(1, 10))
        elements.append(barcode)

        elements.append(
            Paragraph(
                f"<font size=8>Scan to verify receipt</font>",
                styles["Meta"],
            )
        )
        elements.append(Spacer(1, 16))

        elements.append(
            Paragraph(
                f"Issue Date: {receipt.created_at.strftime('%d %B %Y')}",
                styles["Meta"],
            )
        )

        elements.append(Spacer(1, 16))

        property = receipt.property

        elements.append(Paragraph("Property Information", styles["SectionHeader"]))
        property_table = Table(
            [
                ["Property Title", property.title],
                ["Address", property.address],
                ["State / LGA", f"{property.state.name} / {property.lga.name}"],
                ["Property Type", property.property_type.value],
                ["Property Owner", property.owner.full_name],
                ["Property Manager", property.managed_by.full_name],
                ["House Type", property.house_type.value],
            ],
            colWidths=[120, None],
        )

        property_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        elements.append(property_table)
        elements.append(Spacer(1, 14))

        tenant = receipt.tenant

        elements.append(Paragraph("Tenant Information", styles["SectionHeader"]))
        tenant_table = Table(
            [
                [
                    "Tenant Name",
                    f"{tenant.first_name} {tenant.middle_name} {tenant.last_name}",
                ],
                ["Phone Number", tenant.phone_number],
                ["Rent Cycle", tenant.rent_cycle.value],
                [
                    "Rent Period",
                    f"{tenant.rent_start_date} → {tenant.rent_expiry_date}",
                ],
            ],
            colWidths=[120, None],
        )

        tenant_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
                ]
            )
        )

        elements.append(tenant_table)
        elements.append(Spacer(1, 14))

        elements.append(Paragraph("Payment Summary", styles["SectionHeader"]))
        payment_table = Table(
            [
                ["Amount Paid", f"₦{receipt.amount:,.2f}"],
                ["Month / Year", f"{receipt.month_paid_for}/{receipt.year_paid_for}"],
                ["Duration", f"{receipt.rent_duration_months} month(s)"],
                ["Payment Status", "PAID"],
            ],
            colWidths=[120, None],
        )

        payment_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (1, -1), (1, -1), colors.green),
                ]
            )
        )

        elements.append(payment_table)
        elements.append(Spacer(1, 20))

        elements.append(
            Paragraph(
                "This receipt confirms that the rent payment listed above has been "
                "successfully received. Please keep this document for your records.",
                styles["Normal"],
            )
        )

        elements.append(Spacer(1, 12))

        elements.append(
            Paragraph(
                "Generated electronically,",
                styles["Meta"],
            )
        )

        doc.build(elements)

        return file_path
