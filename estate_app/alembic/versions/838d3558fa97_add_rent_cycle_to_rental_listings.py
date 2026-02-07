"""add rent_cycle to rental listings

Revision ID: 838d3558fa97
Revises: a92d96bfd840
Create Date: 2026-02-04 11:28:33.205856
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "838d3558fa97"
down_revision: Union[str, Sequence[str], None] = "a92d96bfd840"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define enum manually for migration
rent_cycle_enum = sa.Enum(
    "Daily",
    "Weekly",
    "Monthly",
    "Yearly",
    name="rentcycle",
    native_enum=False,
)


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Create enum type (needed for some DBs)
    rent_cycle_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add column (nullable first)
    op.add_column(
        "rental_listings",
        sa.Column("rent_cycle", rent_cycle_enum, nullable=True),
    )

    # 3. Fill existing rows
    op.execute(
        "UPDATE rental_listings SET rent_cycle = 'Monthly' WHERE rent_cycle IS NULL"
    )

    # 4. Make NOT NULL
    op.alter_column(
        "rental_listings",
        "rent_cycle",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # 1. Drop column
    op.drop_column("rental_listings", "rent_cycle")

    # 2. Drop enum type
    rent_cycle_enum.drop(op.get_bind(), checkfirst=True)
