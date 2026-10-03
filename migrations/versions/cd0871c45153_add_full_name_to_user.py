"""Add full_name to User

Revision ID: cd0871c45153
Revises: a194a95076ca
Create Date: 2026-09-29 11:16:42.430150

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cd0871c45153'
down_revision = 'a194a95076ca'
branch_labels = None
depends_on = None


def upgrade():
    """Добавляем колонку full_name в таблицу user."""
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('full_name', sa.String(length=200), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('full_name')
