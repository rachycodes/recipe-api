"""Add category to recipes

Revision ID: a97fbd744110
Revises: 72c8ce02f157
Create Date: 2026-11-25 20:04:07.000677

"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision = "a97fbd744110"
down_revision = "72c8ce02f157"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "recipes",
        sa.Column(
            "category",
            sa.String(length=100),
            server_default="Uncategorized",
            nullable=False,
        ),
    )


def downgrade():
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_column("category")