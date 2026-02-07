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
    def _payment_context_paragraph(receipt, property, styles):
        context = receipt.payment_context

        if context == "FULL_RENT":
            return Paragraph(
                "This receipt confirms a full rent payment for the period stated above.",
                styles["Normal"],
            )

        if context == "HALF_RENT":
            return Paragraph(
                f"This receipt confirms an initial part-payment of rent for "
                f"<b>{property.title}</b>. "
                f"The tenant has made a minimum rent payment and is expected to "
                f"clear the remaining balance.",
                styles["Normal"],
            )

        if context == "OUTSTANDING_BALANCE":
            return Paragraph(
                f"This receipt confirms a rent balance settlement for "
                f"<b>{property.title}</b>. "
                f"The tenant is paying off an outstanding rent debt.",
                styles["Normal"],
            )

        return Paragraph(
            "This receipt confirms a rent payment for the period stated above.",
            styles["Normal"],
        )

    @staticmethod
    def generate_pdf(receipt):
        file_path = BASE_PATH / f"{receipt.reference_number}.pdf"
        balance = receipt.expected_amount - receipt.amount_paid
        payment_status = "FULLY PAID" if receipt.fully_paid else "PARTIAL PAYMENT"
        status_color = colors.green if receipt.fully_paid else colors.orange

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
                ["Expected Amount", f"₦{receipt.expected_amount:,.2f}"],
                ["Amount Paid", f"₦{receipt.amount_paid:,.2f}"],
                ["Outstanding Balance", f"₦{max(balance, 0):,.2f}"],
                ["Payment Status", payment_status],
                ["Month / Year", f"{receipt.month_paid_for}/{receipt.year_paid_for}"],
                ["Duration", f"{receipt.rent_duration_months} month(s)"],
            ],
            colWidths=[150, None],
        )

        payment_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (1, -1), (1, -1), colors.green),
                    ("TEXTCOLOR", (1, 3), (1, 3), status_color),
                ]
            )
        )

        elements.append(payment_table)
        elements.append(Spacer(1, 20))
        elements.append(
            ReceiptGenerator._payment_context_paragraph(
                receipt=receipt,
                property=property,
                styles=styles,
            )
        )

        if not receipt.fully_paid:
            elements.append(
                Paragraph(
                    "⚠ This receipt reflects a partial rent payment. "
                    "The outstanding balance must be cleared to fully complete "
                    "the rent cycle.",
                    styles["Normal"],
                )
            )
        elements.append(
            Paragraph(
                "This receipt confirms that the rent payment listed above has been "
                "successfully received. Please keep this document for your records.",
                styles["Normal"],
            )
        )

        elements.append(Spacer(1, 12))

        doc.build(elements)

        return file_path
