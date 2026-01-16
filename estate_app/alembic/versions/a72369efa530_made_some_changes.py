"""made some changes

Revision ID: a72369efa530
Revises: 48052aaccd11
Create Date: 2026-01-11 17:53:09.119654

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography


# revision identifiers, used by Alembic.
revision: str = 'a72369efa530'
down_revision: Union[str, Sequence[str], None] = '48052aaccd11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # 1) Rename is_verified → email_verified
    op.alter_column(
        "users",
        "is_verified",
        new_column_name="email_verified",
        existing_type=sa.Boolean(),
        server_default=sa.false(),
    )

    # 2) Drop location from properties
    op.drop_index("idx_properties_location", table_name="properties")
    op.drop_column("properties", "location")


def downgrade():
    
    op.add_column(
        "properties",
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
    )
    op.create_index("ix_properties_location", "properties", ["location"], postgresql_using="gist")

   
    op.alter_column(
        "users",
        "email_verified",
        new_column_name="is_verified",
        existing_type=sa.Boolean(),
        server_default=sa.false(),
    )

