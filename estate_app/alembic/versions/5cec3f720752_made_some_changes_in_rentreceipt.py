"""made some changes in RentReceipt

Revision ID: 5cec3f720752
Revises: a72369efa530
Create Date: 2026-01-12 14:18:56.690405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5cec3f720752'
down_revision: Union[str, Sequence[str], None] = 'a72369efa530'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "rent_receipts",
        "barcode_reference",
        existing_type=sa.String(length=69),
        nullable=True,
    )

    op.execute(
        "DROP INDEX IF EXISTS uq_rent_receipts_barcode_reference"
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_rent_receipts_barcode_reference
        ON rent_receipts (barcode_reference)
        WHERE barcode_reference IS NOT NULL
        """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_rent_receipts_barcode_reference")

    op.alter_column(
        "rent_receipts",
        "barcode_reference",
        existing_type=sa.String(length=69),
        nullable=False,
    )